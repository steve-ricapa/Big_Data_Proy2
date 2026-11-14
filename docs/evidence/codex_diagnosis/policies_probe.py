"""Read-only Keycloak registration policy and sanitized event inspection."""
import json
import subprocess
code=r'''
import json,httpx
from pathlib import Path
base='http://keycloak:8080/auth'
with httpx.Client(timeout=30) as c:
 r=c.post(base+'/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'ti-admin','password':Path('/run/secrets/admin').read_text().strip()})
 assert r.status_code==200,'Admin auth failed; body suppressed'
 c.headers['Authorization']='Bearer '+r.json()['access_token']
 r=c.get(base+'/admin/realms/ti');r.raise_for_status();realm=r.json()
 out={'eventsEnabled':realm.get('eventsEnabled'),'eventsListeners':realm.get('eventsListeners')}
 r=c.get(base+'/admin/realms/ti/components',params={'type':'org.keycloak.services.clientregistration.policy.ClientRegistrationPolicy'});r.raise_for_status()
 out['registration_policies']=[{'name':p.get('name'),'providerId':p.get('providerId'),'subType':p.get('subType'),'config':{k:v for k,v in p.get('config',{}).items() if k in ('host-sending-registration-request-must-match','trusted-hosts','max-clients','allowed-client-scopes','client-uris-must-match')}} for p in r.json()]
 r=c.get(base+'/admin/realms/ti/events',params={'max':40});out['events_status']=r.status_code
 if r.status_code==200:
  out['events']=[{'time':e.get('time'),'type':e.get('type'),'error':e.get('error'),'clientId':e.get('clientId'),'details':{k:v for k,v in e.get('details',{}).items() if k in ('reason','auth_method','client_auth_method','redirect_uri')}} for e in r.json() if e.get('error')]
 print(json.dumps(out))
'''
p=subprocess.run(['docker','run','--rm','--memory','256m','--network','threat-intelligence_identity','--mount','type=bind,source=/opt/threat-intelligence/secrets/keycloak-admin-password,target=/run/secrets/admin,readonly','--entrypoint','python','ti-app:local','-c',code],capture_output=True,text=True,timeout=120)
assert p.returncode==0,'Read-only probe failed; output suppressed'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
