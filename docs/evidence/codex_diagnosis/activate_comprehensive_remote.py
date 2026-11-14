"""Activate only canary-verified API/MCP code; preserve auth AST and other services."""
import hashlib
import json
import shutil
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path('/opt/threat-intelligence');OUT=ROOT/'docs/evidence/mcp_comprehensive'
stage=json.loads((OUT/'stage.json').read_text());canary=json.loads((OUT/'canary.json').read_text())
assert canary['status']=='PASS_INTEGRATION_NOT_OAUTH_E2E'
def containers():
 p=subprocess.run(['docker','ps','--filter','label=com.docker.compose.project=threat-intelligence','--format','{{.Label "com.docker.compose.service"}} {{.ID}}'],capture_output=True,text=True,check=True)
 return dict(v.split() for v in p.stdout.splitlines())
before=containers()
backup=OUT/'previous_sources';backup.mkdir(exist_ok=False)
created=[]
for name,digest in stage['files'].items():
 source=OUT/'candidate'/name;assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
 target=ROOT/name
 if target.exists():
  previous=backup/name;previous.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,previous)
 else:created.append(name)
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
for kind in ('app','mcp'):
 subprocess.run(['docker','tag',stage['images'][kind]['candidate'],'ti-'+kind+':local'],check=True)
compose=['docker','compose','--project-directory',str(ROOT),'--env-file',str(ROOT/'secrets/public.env')]
for name in ('docker-compose.yml','docker-compose.airflow3.yml','docker-compose.secure.yml','docker-compose.public.yml'):compose+=['-f',str(ROOT/name)]
with (OUT/'activation_compose.log').open('w') as log:
 p=subprocess.run([*compose,'up','-d','--no-deps','--no-build','api','mcp-remote'],stdout=log,stderr=subprocess.STDOUT,timeout=180,check=False)
assert p.returncode==0,'Application activation failed; rollback images retained'
for _ in range(45):
 try:
  with urllib.request.urlopen('http://127.0.0.1:18000/ready',timeout=10) as response:ready=json.load(response)
  if ready.get('status')=='ready':break
 except (OSError,ValueError):pass
 time.sleep(2)
else:raise RuntimeError('Production readiness failed')
after=containers();assert set(before)==set(after)
changed=sorted(k for k in before if before[k]!=after[k]);assert changed==['api','mcp-remote']
result={'at':datetime.now(UTC).isoformat(),'status':'APPLIED_INTERNAL_VALIDATION_PASSED_NATIVE_OAUTH_PENDING','changed_containers':changed,'other_container_ids_unchanged':True,'before':before,'after':after,'created_source_files':created,'source_hashes':stage['files'],'rollback_images':stage['images'],'oauth_verifier_and_security_ast_unchanged':stage['oauth_verifier_and_security_settings_ast_unchanged'],'credentials_changed':False,'historical_data_rewritten':False,'ready':ready}
(OUT/'activation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
