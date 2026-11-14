"""Compare private SM bootstrap references with local files, emitting booleans only."""
import base64
import hmac
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

resource='projects/proyectobigdata2-514216/secrets/ti-dev-runtime-bootstrap/versions/latest'
result={'at':datetime.now(UTC).isoformat(),'resource':resource,'secret_values_emitted':False}
try:
    request=urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'})
    with urllib.request.urlopen(request,timeout=15) as response:
        token=json.load(response)['access_token']
    request=urllib.request.Request('https://secretmanager.googleapis.com/v1/'+resource+':access',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=30) as response:
        payload=json.loads(base64.b64decode(json.load(response)['payload']['data']))
    result['references']={}
    for key in ('mcp-oauth-client-secret','keycloak-user-password'):
        actual=(Path('/opt/threat-intelligence/secrets')/key).read_text().strip()
        present=key in payload
        result['references'][key]={'present_in_bootstrap':present,'matches_runtime_file':present and hmac.compare_digest(payload[key].strip(),actual)}
    result['status']='PASS' if all(r['matches_runtime_file'] for r in result['references'].values()) else 'PARTIAL'
except Exception:
    result['status']='NOT VERIFIED'
print(json.dumps(result))
