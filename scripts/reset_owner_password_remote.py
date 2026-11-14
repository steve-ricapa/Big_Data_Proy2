"""Template: authorized single-user reset, RSA-encrypted delivery only.

Invoked only by reset_owner_password_private.py with a fresh public key.
Never run manually or retry after an ambiguous transport failure.
"""
import json
import subprocess
from pathlib import Path

PUBLIC_KEY_B64 = "__PUBLIC_KEY_B64__"
DELIVERY_ID = "__DELIVERY_ID__"
assert not PUBLIC_KEY_B64.startswith("__"), "Use the private delivery orchestrator"
assert DELIVERY_ID.isalnum(), "Invalid delivery ID"
directory = Path('/opt/threat-intelligence/secrets') / ('owner-reset-' + DELIVERY_ID)
directory.mkdir(mode=0o700, exist_ok=False)
code = r'''
import base64,json,secrets,httpx
from datetime import UTC,datetime
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding
public=serialization.load_pem_public_key(base64.b64decode('__PUBLIC_KEY_B64__'))
base='http://keycloak:8080/auth'
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin authentication failed; body suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token']
 root=base+'/admin/realms/ti'
 r=c.get(root+'/users',params={'username':'ti-owner','exact':'true'})
 assert r.status_code==200 and len(r.json())==1,'Expected exactly one owner'
 user=r.json()[0];assert user['username']=='ti-owner' and user['enabled'] is True
 uid=user['id']
 password='Aa1!'+secrets.token_urlsafe(36)
 ciphertext=public.encrypt(password.encode(),padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
 envelope={'delivery_id':'__DELIVERY_ID__','ciphertext_b64':base64.b64encode(ciphertext).decode(),'algorithm':'RSA-OAEP-SHA256','user':'ti-owner','realm':'ti'}
 # Persist encrypted delivery BEFORE the one authorized reset, for recovery.
 path=Path('/run/delivery/envelope.json')
 with path.open('x') as f:json.dump(envelope,f)
 path.chmod(0o600)
 r=c.put(root+'/users/'+uid+'/reset-password',json={'type':'password','value':password,'temporary':True})
 password=None
 assert r.status_code==204,'Password reset failed; response suppressed; do not retry blindly'
 r=c.get(root+'/users/'+uid);assert r.status_code==200
 current=r.json()
 assert current['enabled'] is True and 'UPDATE_PASSWORD' in current.get('requiredActions',[]),'Reset applied; verify required action before declaring success'
 result={'at':datetime.now(UTC).isoformat(),'status':'READY','user':'ti-owner','realm':'ti','enabled':True,'requiredActions':current.get('requiredActions',[]),'password_temporary':True,'user_login_attempted':False,'other_users_modified':False,'oauth_clients_modified':False,'delivery':envelope}
 print(json.dumps(result))
'''.replace('__PUBLIC_KEY_B64__', PUBLIC_KEY_B64).replace('__DELIVERY_ID__', DELIVERY_ID)
p = subprocess.run([
    'docker', 'run', '--rm', '--user', '0', '--memory', '256m',
    '--network', 'threat-intelligence_identity',
    '--mount', 'type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly',
    '--mount', 'type=bind,source=' + str(directory) + ',target=/run/delivery',
    '--entrypoint', 'python', 'ti-mcp:local', '-c', code,
], capture_output=True, text=True, timeout=120, check=False)
assert p.returncode == 0, 'Reset/delivery did not complete; output suppressed; inspect encrypted recovery envelope before retry'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
