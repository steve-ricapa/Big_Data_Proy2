"""Inspect only ti-owner metadata and MCP authorization configuration, no password values."""
import json
import subprocess

code=r'''
import json,httpx
from datetime import UTC,datetime
from pathlib import Path
base='http://keycloak:8080/auth'
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin authentication failed; response suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token']
 root=base+'/admin/realms/ti'
 def get(path,**kwargs):
  r=c.get(root+path,**kwargs);assert r.status_code==200,'Read-only admin query failed; response suppressed';return r.json()
 users=get('/users',params={'username':'ti-owner','exact':'true'})
 out={'at':datetime.now(UTC).isoformat(),'matching_users':len(users),'user_changes':False,'user_login_attempted':False}
 if len(users)==1:
  u=get('/users/'+users[0]['id']);uid=u['id']
  out['user']={k:u.get(k) for k in ('username','enabled','requiredActions','emailVerified','federationLink')}
  credentials=get('/users/'+uid+'/credentials')
  out['password_credential_present']=any(v.get('type')=='password' for v in credentials)
  out['credential_types']=[v.get('type') for v in credentials]
  out['effective_realm_role_names']=[v['name'] for v in get('/users/'+uid+'/role-mappings/realm/composite')]
  lock=get('/attack-detection/brute-force/users/'+uid)
  out['brute_force']={k:lock.get(k) for k in ('disabled','numFailures','failedLoginNotBefore')}
 realm=get('')
 out['realm']={k:realm.get(k) for k in ('enabled','resetPasswordAllowed','bruteForceProtected','passwordPolicy','browserFlow')}
 out['smtp_configured']=bool(realm.get('smtpServer',{}).get('host'))
 clients=get('/clients',params={'clientId':'ti-codex'});assert len(clients)==1
 client=get('/clients/'+clients[0]['id'])
 out['client']={k:client.get(k) for k in ('clientId','enabled','publicClient','standardFlowEnabled','consentRequired','fullScopeAllowed')}
 defaults=get('/clients/'+client['id']+'/default-client-scopes')
 out['default_client_scopes']=[s['name'] for s in defaults]
 scope=next(s for s in defaults if s['name']=='ti:read')
 detail=get('/client-scopes/'+scope['id'])
 out['scope_attributes']={k:v for k,v in detail.get('attributes',{}).items() if k in ('include.in.token.scope','display.on.consent.screen')}
 mapping=get('/client-scopes/'+scope['id']+'/scope-mappings')
 out['scope_role_restrictions']={'realm':[r['name'] for r in mapping.get('realmMappings',[])],'clients':{k:[r['name'] for r in v.get('mappings',[])] for k,v in mapping.get('clientMappings',{}).items()}}
 out['audience_mapper_matches']=any(m.get('config',{}).get('included.custom.audience')=='https://ti-136-114-21-18.sslip.io/mcp' and m.get('config',{}).get('access.token.claim')=='true' for m in get('/client-scopes/'+scope['id']+'/protocol-mappers/models'))
 out['subject_mapper_present']=any(m.get('protocolMapper')=='oidc-sub-mapper' and m.get('config',{}).get('access.token.claim')=='true' for m in get('/clients/'+client['id']+'/protocol-mappers/models'))
 print(json.dumps(out))
'''
p=subprocess.run(['docker','run','--rm','--memory','256m','--network','threat-intelligence_identity','--mount','type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly','--entrypoint','python','ti-app:local','-c',code],capture_output=True,text=True,timeout=120)
assert p.returncode==0,'Read-only owner inspection failed; raw output suppressed'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
