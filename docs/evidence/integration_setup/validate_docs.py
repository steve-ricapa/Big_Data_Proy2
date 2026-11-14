"""Cross-check documentation/evidence and scan for private values without emitting them."""
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from cloud_test_credentials import load  # noqa: E402

BASE=ROOT/'docs/evidence/integration_setup'
paths=[ROOT/'docs/integrations/chatgpt_mcp_setup.md',ROOT/'docs/report/PROJECT_E2E_COMPLETE.md']
live=json.loads((BASE/'mcp_live.json').read_text(encoding='utf-8'))
calls=json.loads((BASE/'tools_execution.json').read_text(encoding='utf-8'))
assert live['status']=='PASS' and len(live['tools'])==len(calls)==6
assert live['oauth']['refresh_status']==live['oauth']['refresh_client_secret_basic_status']==200
assert live['initialize']['protocolVersion']=='2025-11-25'
assert live['chatgpt_account_connected'] is False
assert all(v['status']=='PASS' for v in calls.values())
assert calls['get_vulnerability_statistics']['result']['total_cves']==174734
assert json.loads((BASE/'secret_reference.json').read_text(encoding='utf-8'))['status']=='PASS'
assert '47 passed, 8 skipped' in (BASE/'local_tests.log').read_text(encoding='utf-8')
credentials=load()  # private IAP transfer, never printed or persisted here
private_values=[v for v in credentials.values() if len(v)>=12]
files=paths+[p for p in BASE.iterdir() if p.suffix in ('.json','.log','.md') and p.name not in ('validation.json','validation.log')]
found=0
for p in files:
    text=p.read_text(encoding='utf-8')
    found+=sum(value in text for value in private_values)
    found+=bool(re.search(r'eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}',text))
assert found==0,'Private material found; values suppressed'
result={'at':datetime.now(UTC).isoformat(),'status':'PASS','six_tools_executed':True,'refresh_post_and_basic':True,'chatgpt_account_connected':False,'private_values_found':found,'documents':{}}
for p in paths:
    text=p.read_text(encoding='utf-8')
    assert sum(line.startswith('```') for line in text.splitlines())%2==0
    broken=[]
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if not target.startswith(('https://','http://','#')) and not (p.parent/target).resolve().exists():
            broken.append(target)
    assert not broken,'Broken local Markdown links'
    result['documents'][str(p.relative_to(ROOT))]={'lines':len(text.splitlines()),'words':len(text.split()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
headings=re.findall(r'^## (\d+)\.',paths[1].read_text(encoding='utf-8'),re.M)
assert list(map(int,headings))==list(range(1,17))
result['e2e_sections']=16
(BASE/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
