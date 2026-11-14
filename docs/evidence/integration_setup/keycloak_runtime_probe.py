"""Read-only OAuth client inspection. Output is an explicit non-secret allowlist."""
import json
import subprocess
from datetime import UTC, datetime

code = r'''
import json,httpx
from pathlib import Path
base='http://keycloak:8080/auth'
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin login failed; body suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token']
 r=c.get(base+'/admin/realms/ti/clients',params={'clientId':'ti-chatgpt'});r.raise_for_status(); clients=r.json();assert len(clients)==1
 internal_id=clients[0]['id']
 r=c.get(base+'/admin/realms/ti/clients/'+internal_id);r.raise_for_status();obj=r.json()
 fields=('clientId','enabled','protocol','publicClient','clientAuthenticatorType','standardFlowEnabled','implicitFlowEnabled','directAccessGrantsEnabled','serviceAccountsEnabled','consentRequired','redirectUris','webOrigins')
 out={'client':{k:obj.get(k) for k in fields}}
 out['client']['attributes']={k:v for k,v in obj.get('attributes',{}).items() if k in ('pkce.code.challenge.method','oauth2.device.authorization.grant.enabled')}
 for kind in ('default','optional'):
  r=c.get(base+'/admin/realms/ti/clients/'+internal_id+'/'+kind+'-client-scopes');r.raise_for_status()
  out[kind+'_client_scopes']=[s['name'] for s in r.json()]
 r=c.get(base+'/admin/realms/ti');r.raise_for_status(); realm=r.json()
 out['realm']={k:realm.get(k) for k in ('realm','enabled','sslRequired','registrationAllowed','bruteForceProtected','accessTokenLifespan','revokeRefreshToken','refreshTokenMaxReuse')}
 r=c.get(base+'/admin/serverinfo');r.raise_for_status();out['keycloak_version']=r.json().get('systemInfo',{}).get('version')
 def safe_mapper(m):
  return {'name':m.get('name'),'protocolMapper':m.get('protocolMapper'),'config':{k:v for k,v in m.get('config',{}).items() if k in ('included.custom.audience','access.token.claim','id.token.claim','introspection.token.claim')}}
 r=c.get(base+'/admin/realms/ti/clients/'+internal_id+'/protocol-mappers/models');r.raise_for_status();out['client_mappers']=[safe_mapper(m) for m in r.json()]
 r=c.get(base+'/admin/realms/ti/client-scopes');r.raise_for_status()
 scopes=r.json();out['realm_client_scope_names']=[s['name'] for s in scopes]
 scope=next(s for s in scopes if s['name']=='ti:read')
 r=c.get(base+'/admin/realms/ti/client-scopes/'+scope['id']+'/protocol-mappers/models');r.raise_for_status();out['ti_read_mappers']=[safe_mapper(m) for m in r.json()]
 print(json.dumps(out))
'''
args = ['docker','run','--rm','--memory','256m','--network','threat-intelligence_identity','--mount','type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly','--entrypoint','python','ti-app:local','-c',code]
p = subprocess.run(args,capture_output=True,text=True,timeout=120)
if p.returncode:
    raise RuntimeError('Read-only Keycloak metadata probe failed; output suppressed')
out=json.loads(p.stdout.splitlines()[-1])
version_code="import json,importlib.metadata as m;from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS;print(json.dumps({'packages':{n:m.version(n) for n in ('mcp','uvicorn','PyJWT')},'supported_protocol_versions':SUPPORTED_PROTOCOL_VERSIONS}))"
p=subprocess.run(['docker','exec','threat-intelligence-mcp-remote-1','python','-c',version_code],capture_output=True,text=True)
out['mcp_runtime']=json.loads(p.stdout) if p.returncode==0 else {'status':'NOT VERIFIED'}
out['at']=datetime.now(UTC).isoformat()
out['config_modified']=False
print(json.dumps(out))
