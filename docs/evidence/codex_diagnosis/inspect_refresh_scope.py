"""Read-only client scopes, role gates and sanitized refresh event inspection."""
import json
import subprocess
code=r'''
import json,httpx
from pathlib import Path
from datetime import UTC,datetime
base='http://keycloak:8080/auth'
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin login failed; body suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token'];root=base+'/admin/realms/ti'
 def get(path,**kwargs):
  r=c.get(root+path,**kwargs);assert r.status_code==200,'Read failed; body suppressed';return r.json()
 clients=get('/clients',params={'clientId':'ti-codex'});assert len(clients)==1
 obj=get('/clients/'+clients[0]['id'])
 out={'at':datetime.now(UTC).isoformat(),'client':{k:obj.get(k) for k in ('clientId','enabled','publicClient','consentRequired','fullScopeAllowed','redirectUris')},'client_attributes':{k:v for k,v in obj.get('attributes',{}).items() if k in ('pkce.code.challenge.method','client.offline.session.idle.timeout','client.offline.session.max.lifespan')}}
 for kind in ('default','optional'):out[kind+'_scopes']=[v['name'] for v in get('/clients/'+obj['id']+'/'+kind+'-client-scopes')]
 scopes=get('/client-scopes');scope=next(v for v in scopes if v['name']=='offline_access')
 out['offline_scope']={'name':scope['name'],'attributes':scope.get('attributes',{})}
 mapping=get('/client-scopes/'+scope['id']+'/scope-mappings')
 out['offline_scope_role_gates']={'realm':[v['name'] for v in mapping.get('realmMappings',[])],'clients':{k:[r['name'] for r in v.get('mappings',[])] for k,v in mapping.get('clientMappings',{}).items()}}
 u=get('/users',params={'username':'ti-owner','exact':'true'});assert len(u)==1
 out['owner_realm_roles']=[v['name'] for v in get('/users/'+u[0]['id']+'/role-mappings/realm/composite')]
 realm=get('');out['realm_offline_settings']={k:realm.get(k) for k in ('offlineSessionIdleTimeout','offlineSessionMaxLifespanEnabled','offlineSessionMaxLifespan','revokeRefreshToken','refreshTokenMaxReuse')}
 events=get('/events',params={'client':'ti-codex','max':60})
 out['events']=[{'time':e.get('time'),'type':e.get('type'),'error':e.get('error'),'details':{k:v for k,v in e.get('details',{}).items() if k in ('scope','reason','grant_type','client_auth_method')}} for e in events]
 print(json.dumps(out))
'''
p=subprocess.run(['docker','run','--rm','--memory','256m','--network','threat-intelligence_identity','--mount','type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly','--entrypoint','python','ti-app:local','-c',code],capture_output=True,text=True,timeout=120,check=False)
assert p.returncode==0,'Scope inspection failed; output suppressed'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
