"""VM bootstrap: executed explicitly as root, only after Terraform created disks.

Uses VM identity for GCS downloads; never logs metadata access tokens.
"""

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--initialize-new-data-disk", action="store_true")
parser.add_argument("--bundle-sha256", required=True)
args = parser.parse_args()
assert os.geteuid() == 0, "Run with sudo"
disk = "/dev/disk/by-id/google-ti-data"
assert Path(disk).exists(), "Expected Terraform data disk missing"
signature = subprocess.run(["blkid", disk], capture_output=True, check=False)
if signature.returncode:
    assert args.initialize_new_data_disk, "Blank disk requires explicit initialization flag"
    size = subprocess.run(["blockdev", "--getsize64", disk], capture_output=True, text=True, check=True).stdout.strip()
    assert int(size) == 100 * 1024 ** 3, "Unexpected disk size"
    mount = subprocess.run(["lsblk", "-n", "-o", "MOUNTPOINTS", disk], capture_output=True, text=True, check=True).stdout.strip()
    assert not mount, "Refusing to format mounted disk"
    subprocess.run(["mkfs.ext4", "-L", "ti-data", disk], check=True)
Path("/srv/ti-data").mkdir(exist_ok=True)
uuid = subprocess.run(["blkid", "-s", "UUID", "-o", "value", disk], capture_output=True, text=True, check=True).stdout.strip()
fstab = Path("/etc/fstab")
if "UUID=" + uuid not in fstab.read_text():
    with fstab.open("a") as stream:
        stream.write(f"\nUUID={uuid} /srv/ti-data ext4 defaults,nofail 0 2\n")
subprocess.run(["mount", "/srv/ti-data"], check=False)
assert os.path.ismount("/srv/ti-data")
root = Path("/opt/threat-intelligence")
root.mkdir(parents=True, exist_ok=True)
raw = "proyectobigdata2-514216-ti-dev-raw"


def download(key, destination):
    request = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(request, timeout=15) as response:
        token = json.load(response)["access_token"]
    url = "https://storage.googleapis.com/storage/v1/b/" + raw + "/o/" + urllib.parse.quote(key, safe="") + "?alt=media"
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".tmp")
    with urllib.request.urlopen(request, timeout=180) as response, temp.open("wb") as stream:
        while block := response.read(1024 * 1024):
            stream.write(block)
    temp.replace(destination)


bundle = Path("/srv/ti-data/ti-cloud-source.tar.gz")
download("releases/ti-cloud-source.tar.gz", bundle)
with bundle.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == args.bundle_sha256
with tarfile.open(bundle, "r:gz") as archive:
    # Stock Debian12 Python can predate tarfile's filter keyword. Reject traversal,
    # links and special entries explicitly before extracting this hash-verified bundle.
    for member in archive:
        destination = (root / member.name).resolve()
        assert destination.is_relative_to(root) and (member.isfile() or member.isdir()), "Unsafe archive member"
        archive.extract(member, root)
subprocess.run(["bash", str(root / "infrastructure/scripts/vm-bootstrap.sh")], check=True)
# All Docker volumes/images go on the explicitly mounted data disk, not boot.
subprocess.run(["systemctl", "stop", "docker", "docker.socket"], check=True)
daemon = Path("/etc/docker/daemon.json")
config = json.loads(daemon.read_text()) if daemon.exists() else {}
assert not Path("/var/lib/docker/containers").exists() or not list(Path("/var/lib/docker/containers").iterdir()), "Refuse relocating existing Docker workloads"
config.update({"data-root": "/srv/ti-data/docker", "log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}})
daemon.write_text(json.dumps(config, indent=2))
subprocess.run(["systemctl", "start", "docker"], check=True)
for year in (2024, 2025, 2026):
    name = f"nvdcve-2.0-{year}.json"
    download(f"nvd/{year}/{name}", root / "data/raw/nvd" / str(year) / name)
for name in ("docs/evidence", "data/staging", "data/processed"):
    (root / name).mkdir(parents=True, exist_ok=True)
for script in ("prepare_local.py", "prepare_security.py", "prepare_airflow3.py"):
    subprocess.run(["python3", str(root / "scripts" / script)], check=True)
for path in (root / "secrets").iterdir():
    # Compose secrets are read-only bind mounts, not Swarm encrypted secrets.
    # Entry points may drop supplementary groups; mounted files must be readable
    # by their dedicated service UID. Host traversal is blocked by parent0700.
    path.chmod(0o444)
    os.chown(path, 0, 0)
(root / "secrets").chmod(0o700)
(root / "data/staging").chmod(0o777)
(root / "docs/evidence").chmod(0o777)
print("Cloud bootstrap complete; dataset downloaded; Docker data-root on persistent disk; private secrets generated.")
