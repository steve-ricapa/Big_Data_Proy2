"""Assign existing offline_access OPTIONAL scope only to ti-codex.

Preserves its role gate: no offline_access role is assigned to any user.
"""
import json
import subprocess
code=r'''
import hashlib,json,httpx
from pathlib import Path
from datetime import UTC,datetime
base='http://keycloak:8080/auth'
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin login failed; body suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token'];root=base+'/admin/realms/ti'
 def get(path,**kwargs):
  r=c.get(root+path,**kwargs);assert r.status_code==200,'Read failed; body suppressed';return r.json()
 clients=get('/clients',params={'clientId':'ti-codex'});assert len(clients)==1
 cid=clients[0]['id'];client_before=get('/clients/'+cid)
 defaults_before=get('/clients/'+cid+'/default-client-scopes')
 optional_before=get('/clients/'+cid+'/optional-client-scopes')
 assert [v['name'] for v in optional_before]==[],'Optional scopes unexpectedly changed; review before applying'
 other=get('/clients',params={'clientId':'ti-chatgpt'});assert len(other)==1
 other_before=get('/clients/'+other[0]['id'])
 other_scopes={k:get('/clients/'+other[0]['id']+'/'+k+'-client-scopes') for k in ('default','optional')}
 policy_before=get('/components',params={'type':'org.keycloak.services.clientregistration.policy.ClientRegistrationPolicy'})
 user=get('/users',params={'username':'ti-owner','exact':'true'});assert len(user)==1
 roles_before=get('/users/'+user[0]['id']+'/role-mappings')
 offline=next(v for v in get('/client-scopes') if v['name']=='offline_access')
 gates_before=get('/client-scopes/'+offline['id']+'/scope-mappings')
 assert any(v['name']=='offline_access' for v in gates_before.get('realmMappings',[])),'Offline scope role gate missing'
 r=c.put(root+'/clients/'+cid+'/optional-client-scopes/'+offline['id'])
 assert r.status_code==204,'Optional scope assignment failed; response suppressed'
 optional_after=get('/clients/'+cid+'/optional-client-scopes')
 assert [v['name'] for v in optional_after]==['offline_access']
 # Keycloak includes scope assignments in the client representation.
 security_before={k:v for k,v in client_before.items() if k not in ('optionalClientScopes','defaultClientScopes')}
 security_after={k:v for k,v in get('/clients/'+cid).items() if k not in ('optionalClientScopes','defaultClientScopes')}
 assert digest(security_before)==digest(security_after)
 assert digest(defaults_before)==digest(get('/clients/'+cid+'/default-client-scopes'))
 assert digest(other_before)==digest(get('/clients/'+other[0]['id']))
 assert all(digest(v)==digest(get('/clients/'+other[0]['id']+'/'+k+'-client-scopes')) for k,v in other_scopes.items())
 assert digest(policy_before)==digest(get('/components',params={'type':'org.keycloak.services.clientregistration.policy.ClientRegistrationPolicy'}))
 assert digest(roles_before)==digest(get('/users/'+user[0]['id']+'/role-mappings'))
 assert digest(gates_before)==digest(get('/client-scopes/'+offline['id']+'/scope-mappings'))
 print(json.dumps({'at':datetime.now(UTC).isoformat(),'status':'APPLIED','client':'ti-codex','optional_scopes_before':[],'optional_scopes_after':['offline_access'],'default_scopes_unchanged':True,'client_security_settings_unchanged':True,'ti_chatgpt_unchanged':True,'dcr_policies_unchanged':True,'user_role_assignments_unchanged':True,'offline_scope_role_gate_unchanged':True,'user_password_changes':False}))
'''
p=subprocess.run(['docker','run','--rm','--memory','256m','--network','threat-intelligence_identity','--mount','type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly','--entrypoint','python','ti-app:local','-c',code],capture_output=True,text=True,timeout=120,check=False)
assert p.returncode==0,'Scope assignment/verification failed; raw output suppressed; inspect before retry'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
