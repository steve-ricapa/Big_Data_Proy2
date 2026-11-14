"""Production SDK/HTTP baseline via operator exec, explicitly not an OAuth E2E."""
import json
import subprocess

code=r'''
import asyncio,json
from datetime import UTC,datetime
from services.mcp_server import server
async def main():
 tools=await server.mcp.list_tools()
 out={'at':datetime.now(UTC).isoformat(),'transport':'internal FastMCP dispatch -> real FastAPI; not OAuth E2E','schemas':{t.name:t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in tools},'calls':{}}
 cases=[('X01_keyword','search_vulnerabilities',{'keyword':'log4j'}),('X01_combined','search_vulnerabilities',{'keyword':'log4j','severity':'CRITICAL'}),('X02_ranking','get_affected_products',{}),('X02_cve','get_affected_products',{'cve_id':'CVE-2021-44228'}),('X03_search','search_vulnerabilities',{'unexpected_parameter':'qa','page_size':1}),('X03_products','get_affected_products',{'limit':1}),('X03_graph','explore_cve_relationships',{'cve_id':'CVE-2021-44228','limit':1}),('X03_cwes','get_top_cwes',{'limit':1}),('X03_cwes_bad','get_top_cwes',{'limit':'bad'}),('X03_stats','get_vulnerability_statistics',{'unexpected_parameter':'qa'}),('X04_detail','get_cve_details',{'cve_id':'CVE-2021-44228'}),('W01_special','search_vulnerabilities',{'keyword':"'\"%_*()[];--",'page_size':1}),('W02_numeric','search_vulnerabilities',{'page':'2','page_size':1}),('W03_missing','get_cve_details',{'cve_id':'CVE-2021-45046'}),('W07_search100','search_vulnerabilities',{'page_size':100})]
 for label,name,args in cases:
  try:
   value=await server.mcp.call_tool(name,args)
   structured=value[1] if isinstance(value,tuple) and len(value)==2 else None
   content=value[0] if isinstance(value,tuple) else value
   texts=[v.text for v in content if hasattr(v,'text')]
   body=structured if structured is not None else json.loads('\n'.join(texts))
   out['calls'][label]={'isError':False,'structuredContent_present_in_sdk_dispatch':structured is not None,'content_characters':sum(map(len,texts)),'result':body}
  except Exception as e:
   out['calls'][label]={'isError':True,'exception_type':type(e).__name__,'message':str(e)[:800]}
 print(json.dumps(out))
asyncio.run(main())
'''
p=subprocess.run(['docker','exec','threat-intelligence-mcp-remote-1','python','-c',code],capture_output=True,text=True,timeout=180,check=False)
assert p.returncode==0,'Internal baseline failed; raw output suppressed'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
