"""One authorized ti-owner reset with current-user DPAPI private delivery.

Does not sign in as ti-owner. No passwords are sent to stdout or argv.
"""
import argparse
import base64
import ctypes
import json
import os
import subprocess
import sys
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ROOT = Path(__file__).resolve().parents[1]


def protect(data):
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    crypt.CryptProtectData.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                                      ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt.CryptProtectData.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not crypt.CryptProtectData(ctypes.byref(source), 'Big Data II private delivery', None, None, None, 1, ctypes.byref(target)):
        raise OSError('DPAPI encryption failed')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorized-reset-ti-owner', action='store_true', required=True)
    parser.parse_args()
    assert os.name == 'nt', 'Requires Windows current-user protection'
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S')
    directory = Path(os.environ['LOCALAPPDATA']) / 'BigDataII' / ('ti-owner-' + stamp)
    directory.mkdir(parents=True, exist_ok=False)
    identity = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                               '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],
                              capture_output=True, text=True, check=True).stdout.strip()
    assert identity.startswith('S-1-5-'), 'Could not resolve Windows identity'
    # No inherited access: only this Windows user and SYSTEM.
    subprocess.run(['icacls.exe', str(directory), '/inheritance:r', '/grant:r',
                    '*' + identity + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                   capture_output=True, check=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    (directory / 'delivery-key.dpapi').write_bytes(protect(private))
    public = base64.b64encode(key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
    template = (ROOT / 'scripts/reset_owner_password_remote.py').read_text(encoding='utf-8')
    script = template.replace('__PUBLIC_KEY_B64__', public).replace('__DELIVERY_ID__', stamp)
    # The generated source contains only the public encryption key, never a password.
    source = directory / 'remote-public-key-script.py'
    source.write_text(script, encoding='utf-8')
    process = subprocess.run([sys.executable, str(ROOT / 'scripts/gcp_remote.py'),
                              '--command', 'sudo python3 -', '--stdin-file', str(source)],
                             cwd=ROOT, capture_output=True, text=True, timeout=240, check=False)
    (directory / 'encrypted-transport-receipt.txt').write_text(process.stdout, encoding='utf-8')
    assert process.returncode == 0, 'Reset status requires recovery inspection; do not repeat; raw output suppressed'
    result = json.loads(next(line for line in process.stdout.splitlines() if line.startswith('{')))
    assert result['status'] == 'READY' and result['user'] == 'ti-owner'
    password = key.decrypt(base64.b64decode(result['delivery']['ciphertext_b64']), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    (directory / 'temporary-password.dpapi').write_bytes(protect(password))
    password = None
    private = None
    viewer = ROOT / 'scripts/view_owner_temporary_password.ps1'
    (directory / 'View-TemporaryPassword.ps1').write_bytes(viewer.read_bytes())
    public_result = {k: v for k, v in result.items() if k != 'delivery'}
    public_result['private_delivery_directory'] = str(directory)
    public_result['protection'] = 'Windows DPAPI CurrentUser; ACL current user and SYSTEM; no plaintext file'
    (ROOT / 'docs/evidence/codex_diagnosis/owner_password_reset.json').write_text(
        json.dumps(public_result, indent=2), encoding='utf-8')
    print(json.dumps(public_result, indent=2))


if __name__ == '__main__':
    main()
