"""Non-interactive checks for the applied Codex native OAuth configuration."""
import base64
import hashlib
import json
import secrets
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

BASE='https://ti-136-114-21-18.sslip.io'
ISSUER=BASE+'/auth/realms/ti'
RESOURCE=BASE+'/mcp'
CALLBACK='http://127.0.0.1:43219/callback/GnTeVrGD9Hed'
NAME='big_data_ii_-_threat_intelligence'
HERE=Path(__file__).resolve().parent
out={'at':datetime.now(UTC).isoformat(),'checks':{},'technical_status':'PENDING_USER_LOGIN','codex_app_e2e':'PENDING'}
checks=out['checks']
home=Path.home()/'.codex'
old=tomllib.loads((home/'config.pre-ti-codex-20261111T0904.toml.bak').read_text())
new=tomllib.loads((home/'config.toml').read_text())
server=new['mcp_servers'][NAME]
assert server['oauth']=={'client_id':'ti-codex'}
assert server['scopes']==['openid','ti:read']
assert new['mcp_oauth_callback_port']==43219
assert new['mcp_oauth_callback_url']=='http://127.0.0.1:43219/callback'
comparable=json.loads(json.dumps(new))
for key in ('mcp_oauth_callback_port','mcp_oauth_callback_url'):comparable.pop(key)
for key in ('scopes','oauth'):comparable['mcp_servers'][NAME].pop(key)
assert comparable==old,'Unrelated configuration changed'
checks['unrelated_configuration_preserved']='PASS'
binary=Path.home()/'AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
p=subprocess.run([str(binary),'mcp','get',NAME,'--json'],capture_output=True,text=True,timeout=20)
assert p.returncode==0,'Codex could not load config; raw output suppressed'
effective=json.loads(p.stdout)
assert effective['transport']['url']==RESOURCE and effective['enabled'] is True
checks['native_config_load']='PASS'
native=json.loads((HERE/'effective_native_callback.json').read_text())
assert native['request']['client_id']=='ti-codex' and native['request']['redirect_uri']==CALLBACK
assert native['request']['code_challenge_method']=='S256'
checks['native_preregistered_authorization_without_dcr']='PASS'
with httpx.Client(timeout=40,follow_redirects=False) as c:
 r=c.get(BASE+'/.well-known/oauth-protected-resource/mcp');assert r.status_code==200
 protected=r.json();assert protected['resource']==RESOURCE and protected['authorization_servers']==[ISSUER] and protected['scopes_supported']==['ti:read']
 r=c.get(BASE+'/.well-known/oauth-authorization-server/auth/realms/ti');assert r.status_code==200
 metadata=r.json();assert metadata['issuer']==ISSUER and 'S256' in metadata['code_challenge_methods_supported']
 assert metadata['authorization_endpoint']==ISSUER+'/protocol/openid-connect/auth'
 assert metadata['token_endpoint']==ISSUER+'/protocol/openid-connect/token'
 r=c.get(ISSUER+'/.well-known/openid-configuration');assert r.status_code==200 and r.json()['issuer']==ISSUER
 r=c.get(metadata['jwks_uri']);assert r.status_code==200 and r.json()['keys']
 checks['discovery_issuer_endpoints_resource_scope_jwks']='PASS'
 challenge=base64.urlsafe_b64encode(hashlib.sha256(secrets.token_bytes(32)).digest()).decode().rstrip('=')
 params={'client_id':'ti-codex','redirect_uri':CALLBACK,'response_type':'code','scope':'openid ti:read','resource':RESOURCE,'code_challenge':challenge,'code_challenge_method':'S256','state':secrets.token_urlsafe(24)}
 r=c.get(metadata['authorization_endpoint'],params=params)
 assert r.status_code==200 and 'name="password"' in r.text,'Configured callback did not reach login form'
 checks['exact_callback_accepted_login_form']='PASS'
 wrong=dict(params,redirect_uri='http://127.0.0.1:43219/callback/wrong')
 r=c.get(metadata['authorization_endpoint'],params=wrong)
 assert r.status_code==400 and 'redirect_uri' in r.text
 checks['unregistered_callback_rejected']='PASS'
 for mode in ('missing','plain'):
  negative=dict(params)
  if mode=='missing':
   negative.pop('code_challenge');negative.pop('code_challenge_method')
  else:negative['code_challenge_method']='plain'
  r=c.get(metadata['authorization_endpoint'],params=negative)
  # Keycloak correctly returns OAuth errors to an already validated redirect.
  location=urlsplit(r.headers.get('location',''))
  assert r.status_code==302 and location.scheme+'://'+location.netloc+location.path==CALLBACK
  assert parse_qs(location.query).get('error')==['invalid_request']
  checks['pkce_'+mode+'_rejected']='PASS'
 for label,headers in (('absent',{}),('invalid',{'Authorization':'Bearer invalid-diagnosis-not-a-token'})):
  r=c.post(RESOURCE,headers={'Accept':'application/json, text/event-stream',**headers},json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'codex-preflight','version':'1'}}})
  assert r.status_code==401 and 'resource_metadata=' in r.headers.get('www-authenticate','')
  checks['unauthorized_'+label+'_rejected']='PASS'
 # An invalid grant must fail without accidentally requiring a confidential-client secret.
 r=c.post(metadata['token_endpoint'],data={'grant_type':'authorization_code','client_id':'ti-codex','code':'invalid-preflight-code','redirect_uri':CALLBACK,'code_verifier':secrets.token_urlsafe(48)})
 assert r.status_code==400 and r.json().get('error')=='invalid_grant'
 checks['public_client_invalid_grant_rejected_without_secret']='PASS'
out['checks_status']='PASS'
out['pending']=['interactive authorization and consent','valid token issuance and signed validation','valid refresh and refreshed-token validation','authenticated initialize/tools-list/six-tools','Codex App UI confirmation']
(HERE/'preflight.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
