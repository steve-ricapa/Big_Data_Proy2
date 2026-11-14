"""Read-only reset staging checks. Never reads plaintext or performs a reset."""
import json
import subprocess
from pathlib import Path

directory=Path('/opt/threat-intelligence/secrets/owner-reset-20261111T163551')
out={'staging_directory_exists':directory.exists(),'encrypted_envelope_exists':(directory/'envelope.json').exists()}
for image in ('ti-app:local','ti-mcp:local'):
 p=subprocess.run(['docker','run','--rm','--memory','128m','--network','none','--entrypoint','python',image,'-c',"import importlib.util,json;print(json.dumps({m:importlib.util.find_spec(m) is not None for m in ('httpx','cryptography')}))"],capture_output=True,text=True,timeout=60,check=False)
 out[image]=json.loads(p.stdout) if p.returncode==0 else {'probe_failed':True}
print(json.dumps(out))
