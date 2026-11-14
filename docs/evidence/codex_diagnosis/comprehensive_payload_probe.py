"""Measure deployed SDK result JSON, not just content text (no OAuth claim)."""
import json
import subprocess
code=r'''
import asyncio,json
from services.mcp_server import server
async def main():
 out={'transport':'operator SDK -> production HTTP; not OAuth E2E','payloads':{}}
 for label,name,args in [('search_legacy100','search_vulnerabilities',{'page_size':100}),('search_summary100','search_vulnerabilities',{'page_size':100,'view':'summary'}),('detail_legacy','get_cve_details',{'cve_id':'CVE-2021-44228'}),('detail_summary','get_cve_details',{'cve_id':'CVE-2021-44228','view':'summary'})]:
  result=await server.mcp.call_tool(name,args)
  assert result.structuredContent is not None and json.loads(result.content[0].text)==result.structuredContent
  out['payloads'][label]={'content_characters':len(result.content[0].text),'result_json_bytes':len(result.model_dump_json(by_alias=True,exclude_none=True).encode()),'includes_structured_and_text':True}
 stats=await server.mcp.call_tool('get_vulnerability_statistics',{})
 out['coverage']=stats.structuredContent['metadata']['coverage']
 out['measurement_notice']='Serialized MCP result object only, excluding HTTP/RPC envelope; dual structured+text intentionally duplicates data for compatibility.'
 print(json.dumps(out))
asyncio.run(main())
'''
p=subprocess.run(['docker','exec','threat-intelligence-mcp-remote-1','python','-c',code],capture_output=True,text=True,timeout=120,check=False)
assert p.returncode==0,'Payload measurement failed; output suppressed'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
