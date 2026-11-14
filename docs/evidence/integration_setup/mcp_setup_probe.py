"""External discovery, PKCE, refresh, negotiated MCP version and real tool calls.

Never persists access/refresh tokens, codes, verifier, password or client secret.
"""
import asyncio
import inspect
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import jwt
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_cloud_mcp as probe  # noqa: E402
from cloud_test_credentials import load  # noqa: E402

OUT=ROOT/'docs/evidence/integration_setup'
BASE=probe.BASE
ISSUER=probe.ISSUER


async def main():
    evidence={'at':datetime.now(UTC).isoformat(),'endpoint':BASE+'/mcp','discovery':{}}
    with httpx.Client(timeout=45) as client:
        for path in ('/.well-known/oauth-protected-resource/mcp','/.well-known/oauth-protected-resource','/.well-known/oauth-authorization-server/auth/realms/ti','/auth/realms/ti/.well-known/openid-configuration'):
            r=client.get(BASE+path)
            evidence['discovery'][path]={'status':r.status_code,'body':r.json() if r.status_code==200 else None}
        r=client.post(BASE+'/mcp',headers={'Accept':'application/json, text/event-stream'},json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'ti-doc-verifier','version':'1.0'}}})
        evidence['unauthenticated_initialize']={'status':r.status_code,'www_authenticate':r.headers.get('www-authenticate')}
        assert r.status_code==401
        r=client.get(ISSUER+'/protocol/openid-connect/certs');assert r.status_code==200
        evidence['jwks']={'status':r.status_code,'keys':len(r.json()['keys'])}
    credentials=load()
    # Instrument only the local test function to retain token metadata in memory.
    source=inspect.getsource(probe.authorize).replace('return tokens["access_token"]', 'return tokens, query.get("iss", [None])[0]')
    # Test refresh on a NORMAL grant. Replaying a code can invalidate its
    # Keycloak session; test that negative case with a separate login below.
    source=source.replace('        replay = client.post(metadata["token_endpoint"], data=data)\n        assert replay.status_code == 400 and replay.json()["error"] == "invalid_grant"\n','')
    namespace=dict(vars(probe));exec(source,namespace)
    tokens,callback_issuer=namespace['authorize'](credentials)
    token=tokens['access_token']
    evidence['oauth']={'pkce_s256':'PASS','callback_issuer':callback_issuer,'callback_issuer_matches':callback_issuer==ISSUER,'expires_in':tokens.get('expires_in'),'refresh_token_present':bool(tokens.get('refresh_token')),'scope':tokens.get('scope')}
    if tokens.get('refresh_token'):
        with httpx.Client(timeout=45) as client:
            r=client.post(ISSUER+'/protocol/openid-connect/token',data={'grant_type':'refresh_token','refresh_token':tokens['refresh_token'],'client_id':'ti-chatgpt','client_secret':credentials['mcp-oauth-client-secret'],'resource':BASE+'/mcp'})
            evidence['oauth']['refresh_status']=r.status_code
            if r.status_code==200:
                renewed=r.json()
                token=renewed['access_token']
                if renewed.get('refresh_token'):
                    basic=client.post(ISSUER+'/protocol/openid-connect/token',auth=httpx.BasicAuth('ti-chatgpt',credentials['mcp-oauth-client-secret']),data={'grant_type':'refresh_token','refresh_token':renewed['refresh_token'],'resource':BASE+'/mcp'})
                    evidence['oauth']['refresh_client_secret_basic_status']=basic.status_code
                    if basic.status_code==200:
                        token=basic.json()['access_token']
            else:
                error=r.json().get('error')
                evidence['oauth']['refresh_error']=error if error in ('invalid_grant','invalid_scope','invalid_client','unauthorized_client','unsupported_grant_type') else 'error-body-suppressed'
    claims=jwt.decode(token,options={'verify_signature':False})
    evidence['oauth']['issued_claims']={k:claims.get(k) for k in ('iss','aud','scope')}
    async with httpx.AsyncClient(headers={'Authorization':'Bearer '+token},timeout=60) as client, streamable_http_client(BASE+'/mcp',http_client=client) as streams, ClientSession(streams[0],streams[1]) as session:
        init=await session.initialize()
        evidence['initialize']=init.model_dump(mode='json',by_alias=True,exclude_none=True)
        tools=(await session.list_tools()).tools
        assert len(tools)==6
        evidence['tools']=[t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in tools]
        calls={}
        found=await session.call_tool('search_vulnerabilities',{'page_size':1});assert not found.isError
        calls['search_vulnerabilities']={'arguments':{'page_size':1},'result':json.loads(found.content[0].text),'status':'PASS'}
        identifier=calls['search_vulnerabilities']['result']['items'][0]['cve_id']
        for name,args in (('get_cve_details',{'cve_id':identifier}),('get_top_cwes',{}),('get_vulnerability_statistics',{}),('get_affected_products',{}),('explore_cve_relationships',{'cve_id':identifier})):
            result=await session.call_tool(name,args);assert not result.isError,name
            calls[name]={'arguments':args,'result':json.loads(result.content[0].text),'status':'PASS'}
        invalid=await session.call_tool('get_cve_details',{'cve_id':'../../secrets'})
        evidence['invalid_identifier_rejected']=bool(invalid.isError)
        assert invalid.isError
    evidence['chatgpt_account_connected']=False
    probe.authorize(credentials)  # Independent negative code-replay check.
    evidence['oauth']['code_replay_rejected']='PASS'
    evidence['status']='PASS' if evidence['oauth'].get('refresh_status')==200 and evidence['oauth'].get('refresh_client_secret_basic_status')==200 else 'PARTIAL'
    (OUT/'mcp_live.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    (OUT/'tools_execution.json').write_text(json.dumps(calls,indent=2),encoding='utf-8')
    print(json.dumps({'at':evidence['at'],'status':evidence['status'],'protocol':evidence['initialize']['protocolVersion'],'server':evidence['initialize']['serverInfo'],'tools':list(calls),'refresh_status':evidence['oauth'].get('refresh_status'),'example_cve':identifier,'chatgpt_account_connected':False}))


if __name__=='__main__':
    asyncio.run(main())
