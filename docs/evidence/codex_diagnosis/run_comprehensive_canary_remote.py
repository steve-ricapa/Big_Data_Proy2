"""Candidate loopback API + real-HTTP SDK verification; no public ports/auth bypass."""
import base64
import json
import subprocess
import time
import zlib
from pathlib import Path

VERIFICATION='__PUBLIC_VERIFICATION__'
ROOT=Path('/opt/threat-intelligence')
OUT=ROOT/'docs/evidence/mcp_comprehensive'
data=json.loads(zlib.decompress(base64.b64decode(VERIFICATION)))
verify=OUT/'verification';verify.mkdir(exist_ok=True)
for name in ('suite.py','nvd.json'):
 (verify/name).write_bytes(base64.b64decode(data[name]))
container='threat-intelligence-api-1'
subprocess.run(['docker','exec',container,'python','-c',"import socket; s=socket.socket();s.bind(('127.0.0.1',18002));s.close()"],check=True,capture_output=True)
subprocess.run(['docker','exec',container,'mkdir','-p','/tmp/ti-comprehensive/services'],check=True)
subprocess.run(['docker','cp',str(OUT/'candidate/services')+'/.',container+':/tmp/ti-comprehensive/services'],check=True)
boot="import os,sys;from pathlib import Path;sys.path.insert(0,'/tmp/ti-comprehensive');Path('/tmp/ti-comprehensive/api.pid').write_text(str(os.getpid()));import uvicorn;uvicorn.run('services.api.app:app',host='127.0.0.1',port=18002,log_level='warning',access_log=False)"
subprocess.run(['docker','exec','-d',container,'python','-c',boot],check=True)
try:
 for _ in range(30):
  ready=subprocess.run(['docker','exec',container,'python','-c',"import json,urllib.request;assert json.load(urllib.request.urlopen('http://127.0.0.1:18002/ready',timeout=10))['status']=='ready'"],capture_output=True,text=True,check=False)
  if ready.returncode==0:break
  time.sleep(1)
 else:raise RuntimeError('Canary API readiness failed; production listener unchanged')
 p=subprocess.run(['docker','run','--rm','--memory','384m','--network','container:'+container,'--env','PYTHONPATH=/app:/app/src','--env','API_URL=http://127.0.0.1:18002','--env','NVD_FIXTURE=/verification/nvd.json','--mount','type=bind,source='+str(verify)+',target=/verification,readonly','--entrypoint','python','ti-mcp:comprehensive20261111','/verification/suite.py'],capture_output=True,text=True,timeout=600,check=False)
 lines=[line for line in p.stdout.splitlines() if line.startswith('{')]
 result=json.loads(lines[-1]) if lines else {'status':'FAIL_NO_STRUCTURED_RESULT','exit':p.returncode}
 (OUT/'canary.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result))
 assert p.returncode==0 and result['status']=='PASS_INTEGRATION_NOT_OAUTH_E2E','Candidate failed: production not activated'
finally:
 stop="import os,signal;from pathlib import Path;p=int(Path('/tmp/ti-comprehensive/api.pid').read_text());cmd=Path('/proc/'+str(p)+'/cmdline');assert cmd.exists() and b'ti-comprehensive' in cmd.read_bytes();os.kill(p,signal.SIGTERM)"
 stopped=subprocess.run(['docker','exec',container,'python','-c',stop],capture_output=True,text=True,check=False)
 print(json.dumps({'canary_stop_exit':stopped.returncode,'production_api_restarted':False,'public_ports_added':False}))
