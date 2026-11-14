"""Operator SDK -> deployed HTTP API, no OAuth credential access or data writes."""
import base64
import json
import subprocess
import zlib
from pathlib import Path

VERIFICATION='__PUBLIC_VERIFICATION__'
OUT=Path('/opt/threat-intelligence/docs/evidence/mcp_comprehensive')
verify=OUT/'verification'
data=json.loads(zlib.decompress(base64.b64decode(VERIFICATION)))
for name in ('suite.py','nvd.json'):(verify/name).write_bytes(base64.b64decode(data[name]))
image=subprocess.run(['docker','inspect','--format','{{.Image}}','threat-intelligence-mcp-remote-1'],capture_output=True,text=True,check=True).stdout.strip()
p=subprocess.run(['docker','run','--rm','--memory','384m','--network','threat-intelligence_edge','--env','PYTHONPATH=/app:/app/src','--env','API_URL=http://api:8000','--env','NVD_FIXTURE=/verification/nvd.json','--mount','type=bind,source='+str(verify)+',target=/verification,readonly','--entrypoint','python',image,'/verification/suite.py'],capture_output=True,text=True,timeout=600,check=False)
lines=[line for line in p.stdout.splitlines() if line.startswith('{')]
result=json.loads(lines[-1]) if lines else {'status':'FAIL_NO_JSON','exit':p.returncode}
result['deployed_mcp_image_id']=image
(OUT/'production_integration.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
assert p.returncode==0 and result['status']=='PASS_INTEGRATION_NOT_OAUTH_E2E','Production integration failed; do not declare complete'
