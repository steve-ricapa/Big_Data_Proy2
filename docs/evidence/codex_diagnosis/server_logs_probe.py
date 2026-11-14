"""Bounded server-log inspection: no headers, query values or secret config output."""
import json
import re
import subprocess
from datetime import UTC, datetime
from urllib.parse import urlsplit

out={'at':datetime.now(UTC).isoformat(),'window':'last 3h, bounded 2500 lines per service','services':{}}
for service in ('caddy','keycloak','mcp-remote'):
    p=subprocess.run(['docker','logs','--since','3h','--tail','2500',f'threat-intelligence-{service}-1'],capture_output=True,text=True)
    records=[]
    for line in (p.stdout+'\n'+p.stderr).splitlines():
        try:d=json.loads(line)
        except ValueError:d=None
        if service=='caddy' and isinstance(d,dict) and 'request' in d:
            request=d['request'];path=urlsplit(request.get('uri','')).path
            if not any(part in path for part in ('mcp','well-known','/auth/')):continue
            ua=' '.join(request.get('headers',{}).get('User-Agent',[]))
            records.append({'ts':d.get('ts'),'method':request.get('method'),'path':path,'status':d.get('status'),'duration':d.get('duration'),'ua_family':next((v for v in ('codex','rmcp','python-httpx','reqwest','Mozilla') if v.lower() in ua.lower()),'other')})
        elif service!='caddy' and re.search(r'(?i)(error|warn|register|registration|invalid|reject|oauth|client_id)',line):
            # All tokens/quoted details are dropped; emit only known error labels.
            labels=re.findall(r'(?i)(invalid_client|invalid_redirect_uri|invalid_scope|invalid_grant|insufficient_scope|unauthorized_client|client_not_found|client_registration_error|register_error|registration|not.allowed|not.permitted|ClientRegistrationPolicyException|Forbidden|AuthenticationError|OIDC verification rejected|InvalidAudienceError|InvalidIssuerError|ExpiredSignatureError|MissingRequiredClaimError)',line)
            if labels:
                stamp=re.search(r'\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:[.,]\d+)?',line)
                records.append({'time':stamp.group(0) if stamp else None,'labels':labels})
    out['services'][service]={'docker_logs_exit':p.returncode,'matches':records[-250:]}
print(json.dumps(out))
