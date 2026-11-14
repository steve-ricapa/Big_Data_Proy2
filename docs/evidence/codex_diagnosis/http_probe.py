"""Public OAuth discovery and negative redirect validation; no login or tokens."""
import json,secrets,hashlib,base64
from datetime import UTC,datetime
from pathlib import Path
import httpx
base='https://ti-136-114-21-18.sslip.io'
issuer=base+'/auth/realms/ti'
out={'at':datetime.now(UTC).isoformat(),'discovery':{}}
with httpx.Client(timeout=40,follow_redirects=False) as c:
 for path in ('/.well-known/oauth-protected-resource/mcp','/.well-known/oauth-protected-resource','/.well-known/oauth-authorization-server/auth/realms/ti','/auth/realms/ti/.well-known/openid-configuration'):
  r=c.get(base+path)
  out['discovery'][path]={'status':r.status_code,'metadata':r.json() if r.status_code==200 else None}
 r=c.post(base+'/mcp',headers={'Accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'ti-codex-diagnosis','version':'1'}}})
 out['unauthenticated_initialize']={'status':r.status_code,'www_authenticate':r.headers.get('www-authenticate')}
 challenge=base64.urlsafe_b64encode(hashlib.sha256(secrets.token_bytes(32)).digest()).decode().rstrip('=')
 r=c.get(issuer+'/protocol/openid-connect/auth',params={'client_id':'ti-chatgpt','redirect_uri':'http://127.0.0.1:43219/callback','response_type':'code','scope':'openid ti:read','code_challenge':challenge,'code_challenge_method':'S256','state':secrets.token_urlsafe(20),'resource':base+'/mcp'})
 out['existing_client_codex_callback']={'status':r.status_code,'invalid_redirect_uri':('Invalid parameter: redirect_uri' in r.text),'redirected':r.is_redirect}
assert out['unauthenticated_initialize']['status']==401
assert out['existing_client_codex_callback']['invalid_redirect_uri']
Path(__file__).with_name('http.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'at':out['at'],'challenge':out['unauthenticated_initialize'],'callback_test':out['existing_client_codex_callback']},indent=2))
