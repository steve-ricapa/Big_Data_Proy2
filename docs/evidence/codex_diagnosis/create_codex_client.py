"""Authorized, create-only Keycloak native client; never prints credentials."""
import json
import subprocess

code=r'''
import hashlib,json,httpx
from pathlib import Path
from datetime import UTC,datetime
base='http://keycloak:8080/auth'
callback='http://127.0.0.1:43219/callback/GnTeVrGD9Hed'
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin authentication failed; body suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token']
 root=base+'/admin/realms/ti'
 def get(path,**kwargs):
  r=c.get(root+path,**kwargs);r.raise_for_status();return r.json()
 previous=get('/clients',params={'clientId':'ti-chatgpt'});assert len(previous)==1
 old=get('/clients/'+previous[0]['id'])
 old_scopes={kind:get('/clients/'+old['id']+'/'+kind+'-client-scopes') for kind in ('default','optional')}
 policy=get('/components',params={'type':'org.keycloak.services.clientregistration.policy.ClientRegistrationPolicy'})
 assert not get('/clients',params={'clientId':'ti-codex'}),'Client already exists; refusing overwrite'
 scope=next(s for s in get('/client-scopes') if s['name']=='ti:read')
 scope_mappers=get('/client-scopes/'+scope['id']+'/protocol-mappers/models')
 assert any(m.get('config',{}).get('included.custom.audience')=='https://ti-136-114-21-18.sslip.io/mcp' and m.get('config',{}).get('access.token.claim')=='true' for m in scope_mappers)
 subject=next(m for m in get('/clients/'+old['id']+'/protocol-mappers/models') if m['protocolMapper']=='oidc-sub-mapper')
 subject={k:v for k,v in subject.items() if k!='id'}
 payload={'clientId':'ti-codex','name':'Codex native MCP','enabled':True,'protocol':'openid-connect','publicClient':True,'standardFlowEnabled':True,'implicitFlowEnabled':False,'directAccessGrantsEnabled':False,'serviceAccountsEnabled':False,'consentRequired':True,'fullScopeAllowed':False,'redirectUris':[callback],'webOrigins':[],'attributes':{'pkce.code.challenge.method':'S256','oauth2.device.authorization.grant.enabled':'false','backchannel.logout.session.required':'true'},'defaultClientScopes':['ti:read'],'optionalClientScopes':[],'protocolMappers':[subject]}
 r=c.post(root+'/clients',json=payload);assert r.status_code==201,'Client creation failed; body suppressed'
 created=get('/clients',params={'clientId':'ti-codex'});assert len(created)==1
 client=get('/clients/'+created[0]['id'])
 scopes={kind:[s['name'] for s in get('/clients/'+client['id']+'/'+kind+'-client-scopes')] for kind in ('default','optional')}
 assert scopes=={'default':['ti:read'],'optional':[]},'Unexpected scopes; inspect newly created client'
 for key in ('publicClient','standardFlowEnabled','consentRequired'):assert client[key] is True
 for key in ('implicitFlowEnabled','directAccessGrantsEnabled','serviceAccountsEnabled','fullScopeAllowed'):assert client[key] is False
 assert client['redirectUris']==[callback]
 assert client['attributes']['pkce.code.challenge.method']=='S256'
 assert digest(old)==digest(get('/clients/'+old['id'])),'Existing ChatGPT client changed'
 assert all(digest(v)==digest(get('/clients/'+old['id']+'/'+kind+'-client-scopes')) for kind,v in old_scopes.items())
 assert digest(policy)==digest(get('/components',params={'type':'org.keycloak.services.clientregistration.policy.ClientRegistrationPolicy'})),'Registration policies changed'
 realm=get('')
 out={'at':datetime.now(UTC).isoformat(),'status':'PASS','created':True,'client':{k:client.get(k) for k in payload if k not in ('protocolMappers','defaultClientScopes','optionalClientScopes')},'scopes':scopes,'subject_mapper_present':any(m['protocolMapper']=='oidc-sub-mapper' for m in get('/clients/'+client['id']+'/protocol-mappers/models')),'audience_mapping_verified':True,'ti_chatgpt_unchanged':True,'dcr_policies_unchanged':True,'realm_token_settings':{k:realm.get(k) for k in ('accessTokenLifespan','revokeRefreshToken','refreshTokenMaxReuse')}}
 print(json.dumps(out))
'''
p=subprocess.run(['docker','run','--rm','--memory','256m','--network','threat-intelligence_identity','--mount','type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly','--entrypoint','python','ti-app:local','-c',code],capture_output=True,text=True,timeout=120)
assert p.returncode==0,'Create-only Keycloak operation failed; raw output suppressed; inspect new client before retry'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
