"""Activate only the API/MCP application images, preserve every other container."""
import hashlib
import json
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path('/opt/threat-intelligence')
OUT=ROOT/'docs/evidence/codex_functional'
release=json.loads((OUT/'release_staged.json').read_text())
backfill=json.loads((OUT/'backfill_execution.json').read_text())
assert backfill['exit']==0 and any(r.get('status')=='PASS' for r in backfill['records'])
def containers():
 p=subprocess.run(['docker','ps','--filter','label=com.docker.compose.project=threat-intelligence','--format','{{.Label "com.docker.compose.service"}} {{.ID}}'],capture_output=True,text=True,check=True)
 return dict(line.split() for line in p.stdout.splitlines())
def remote_auth_hash():
 p=subprocess.run(['docker','exec','threat-intelligence-mcp-remote-1','python','-c',"import hashlib;from pathlib import Path;print(hashlib.sha256(Path('/app/services/mcp_server/remote.py').read_bytes()).hexdigest())"],capture_output=True,text=True,check=True)
 return p.stdout.strip()
before=containers();auth_before=remote_auth_hash()
for kind in ('app','mcp'):
 subprocess.run(['docker','tag',release['images'][kind]['tag'],'ti-'+kind+':local'],check=True)
compose=['docker','compose','--project-directory',str(ROOT),'--env-file',str(ROOT/'secrets/public.env')]
for name in ('docker-compose.yml','docker-compose.airflow3.yml','docker-compose.secure.yml','docker-compose.public.yml'):
 compose+=['-f',str(ROOT/name)]
with (OUT/'activation_compose.log').open('w') as log:
 p=subprocess.run([*compose,'up','-d','--no-deps','--no-build','api','mcp-remote'],stdout=log,stderr=subprocess.STDOUT,timeout=180,check=False)
assert p.returncode==0,'Application activation failed; inspect bounded compose log'
deadline=time.monotonic()+90
while time.monotonic()<deadline:
 try:
  with urllib.request.urlopen('http://127.0.0.1:18000/ready',timeout=10) as response:
   ready=json.load(response)
  if ready.get('status')=='ready':break
 except (OSError,ValueError):pass
 time.sleep(2)
else:raise RuntimeError('Application readiness timeout')
after=containers()
assert set(before)==set(after)
changed=sorted(k for k in before if before[k]!=after[k])
assert changed==['api','mcp-remote'],'Unexpected container changes'
assert auth_before==remote_auth_hash(),'Remote OAuth verifier changed unexpectedly'
result={'at':datetime.now(UTC).isoformat(),'status':'PASS','changed_containers':changed,'other_container_ids_unchanged':True,'before':before,'after':after,'ready':ready,'oauth_verifier_sha256':auth_before,'oauth_verifier_unchanged':True,'rollback_tags':{kind:release['images'][kind]['previous_tag'] for kind in ('app','mcp')}}
(OUT/'activation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
