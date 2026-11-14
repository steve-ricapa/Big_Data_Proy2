"""Read MCP inventory through a real Codex app-server, never exposing credentials."""
import argparse
import json
import os
import queue
import re
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

NAME='big_data_ii_-_threat_intelligence'
parser=argparse.ArgumentParser()
parser.add_argument('--binary',choices=['npm','app'],required=True)
parser.add_argument('--call-readonly-stats',action='store_true')
parser.add_argument('--functional-suite',action='store_true')
parser.add_argument('--comprehensive-baseline',action='store_true')
parser.add_argument('--evidence-name',default=None)
args=parser.parse_args()
home=Path.home()
binary=(home/'AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe' if args.binary=='npm' else home/'AppData/Local/OpenAI/Codex/bin/9e1da79431da526b/codex.exe')
out={'at':datetime.now(UTC).isoformat(),'probe':'separate native app-server process; NOT the already running App process','binary':str(binary),'version':subprocess.run([str(binary),'--version'],capture_output=True,text=True,check=True).stdout.strip(),'CODEX_HOME':str(home/'.codex'),'persistent_config_modified':False}
process=subprocess.Popen([str(binary),'-c','mcp_servers.node_repl.enabled=false','app-server','--stdio'],cwd=Path(__file__).resolve().parents[3],env=dict(os.environ,CODEX_HOME=str(home/'.codex')),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',bufsize=1)
messages=queue.Queue();labels=[]
def stdout():
 for line in process.stdout:
  try:messages.put(json.loads(line))
  except ValueError:pass
def stderr():
 for line in process.stderr:
  matches=re.findall(r'(?i)(invalid_grant|invalid_client|invalid_token|AuthRequired|Auth required|Unauthorized|Forbidden|timed out|timeout|401|403|404|refresh failed|handshaking|Connection closed|token expired)',line)
  if matches:labels.append(matches)
threading.Thread(target=stdout,daemon=True).start()
threading.Thread(target=stderr,daemon=True).start()
counter=0
def request(method,params):
 global counter
 counter+=1;rid=counter
 process.stdin.write(json.dumps({'jsonrpc':'2.0','id':rid,'method':method,'params':params})+'\n');process.stdin.flush()
 deadline=time.monotonic()+75
 while time.monotonic()<deadline:
  try:message=messages.get(timeout=0.4)
  except queue.Empty:
   assert process.poll() is None,'Native process exited before response'
   continue
  if message.get('id')==rid:
   if 'error' in message:
    out.setdefault('rpc_errors',[]).append({'method':method,'code':message['error'].get('code')})
    raise RuntimeError('RPC request failed; error message suppressed')
   return message.get('result',{})
 raise TimeoutError('Native inventory request timed out')
try:
 init=request('initialize',{'clientInfo':{'name':'ti-native-mcp-diagnostic','version':'1.0'},'capabilities':{'experimentalApi':True}})
 out['native_initialize']='PASS'
 process.stdin.write(json.dumps({'jsonrpc':'2.0','method':'initialized'})+'\n');process.stdin.flush()
 config=request('config/read',{'includeLayers':False,'cwd':str(Path(__file__).resolve().parents[3])})
 target=config.get('config',{}).get('mcp_servers',{}).get(NAME,{})
 out['effective_target_config']={k:target[k] for k in ('url','enabled','scopes','enabled_tools','disabled_tools','startup_timeout_sec','required','environment_id') if k in target}
 out['effective_client_id']=target.get('oauth',{}).get('client_id')
 result=request('mcpServerStatus/list',{'detail':'full','limit':100})
 out['unscoped_inventory']=[{'name':s['name'],'authStatus':s.get('authStatus'),'tool_count':len(s.get('tools',{}))} for s in result.get('data',[]) if s.get('name')==NAME]
 thread=request('thread/start',{'cwd':str(Path(__file__).resolve().parents[3]),'ephemeral':True,'sandbox':'read-only','approvalPolicy':'on-request'})
 thread_id=thread['thread']['id']
 out['ephemeral_thread_started']=True
 # No model turn or user prompt is submitted. Let native MCP startup complete.
 for attempt in range(10):
  result=request('mcpServerStatus/list',{'detail':'full','limit':100,'threadId':thread_id})
  matching=[s for s in result.get('data',[]) if s.get('name')==NAME]
  if matching and len(matching[0].get('tools',{}))==6:break
  time.sleep(2)
 statuses=[s for s in result.get('data',[]) if s.get('name')==NAME]
 out['target_present']=bool(statuses)
 if statuses:
  s=statuses[0]
  out['target']={'name':s['name'],'authStatus':s.get('authStatus'),'tool_count':len(s.get('tools',{})),'tool_names':sorted(s.get('tools',{})),'resource_count':len(s.get('resources',[])),'resource_template_count':len(s.get('resourceTemplates',[])),'serverInfo':s.get('serverInfo')}
 out['status']='DISCOVERED_SIX' if statuses and len(statuses[0].get('tools',{}))==6 else 'NOT_SIX'
 if args.comprehensive_baseline and out['status']=='DISCOVERED_SIX':
  out['schemas']={name:{k:tool.get(k) for k in ('name','description','inputSchema','outputSchema')} for name,tool in s['tools'].items()}
  out['baseline_calls']={}
  cases=[
   ('X01_keyword','search_vulnerabilities',{'keyword':'log4j'}),
   ('X01_severity','search_vulnerabilities',{'severity':'CRITICAL','page_size':1}),
   ('X01_combined','search_vulnerabilities',{'keyword':'log4j','severity':'CRITICAL'}),
   ('X01_exact','search_vulnerabilities',{'cve_id':'CVE-2021-44228'}),
   ('X02_ranking','get_affected_products',{}),
   ('X02_cve','get_affected_products',{'cve_id':'CVE-2021-44228'}),
   ('X03_search_unknown','search_vulnerabilities',{'unexpected_parameter':'qa','page_size':1}),
   ('X03_products_limit','get_affected_products',{'limit':1}),
   ('X03_graph_limit','explore_cve_relationships',{'cve_id':'CVE-2021-44228','limit':1}),
   ('X03_cwes_limit','get_top_cwes',{'limit':1}),
   ('X03_cwes_bad_limit','get_top_cwes',{'limit':'bad'}),
   ('X03_statistics_unknown','get_vulnerability_statistics',{'unexpected_parameter':'qa'}),
   ('X04_details','get_cve_details',{'cve_id':'CVE-2021-44228'}),
   ('W01_special','search_vulnerabilities',{'keyword':"'\"%_*()[];--",'page_size':1}),
   ('W02_coercion','search_vulnerabilities',{'page':'2','page_size':1}),
   ('W03_missing','get_cve_details',{'cve_id':'CVE-2021-45046'}),
   ('W07_payload','search_vulnerabilities',{'page_size':100}),
  ]
  for label,tool,arguments in cases:
   call=request('mcpServer/tool/call',{'threadId':thread_id,'server':NAME,'tool':tool,'arguments':arguments})
   body=call.get('structuredContent')
   parts=[v.get('text','') for v in call.get('content',[]) if v.get('type')=='text']
   if body is None:
    try:body=json.loads('\n'.join(parts))
    except ValueError:body={'message':'\n'.join(parts)[:1500]}
   out['baseline_calls'][label]={'tool':tool,'arguments':arguments,'isError':bool(call.get('isError')),'structuredContent_present':call.get('structuredContent') is not None,'content_characters':sum(map(len,parts)),'result':body}
  out['status']='BASELINE_CAPTURED'
 if args.functional_suite and out['status']=='DISCOVERED_SIX':
  out['tool_input_fields']={name:sorted(tool.get('inputSchema',{}).get('properties',{})) for name,tool in s.get('tools',{}).items()}
  out['functional_calls']={}
  cases=[
   ('search_exact','search_vulnerabilities',{'cve_id':'CVE-2021-44228'}),
   ('details','get_cve_details',{'cve_id':'CVE-2021-44228'}),
   ('cwes','get_top_cwes',{}),
   ('stats','get_vulnerability_statistics',{}),
   ('products','get_affected_products',{'cve_id':'CVE-2021-44228'}),
   ('relationships','explore_cve_relationships',{'cve_id':'CVE-2021-44228'}),
   ('keyword','search_vulnerabilities',{'keyword':'log4j','page_size':5}),
   ('severity','search_vulnerabilities',{'severity':'CRITICAL','page_size':5}),
   ('combined','search_vulnerabilities',{'keyword':'log4j','severity':'CRITICAL','cve_id':'CVE-2021-44228'}),
   ('negative_combined','search_vulnerabilities',{'severity':'LOW','cve_id':'CVE-2021-44228'}),
   ('keyword_no_match','search_vulnerabilities',{'keyword':'tiunlikelynomatchterm20261111'}),
   ('legacy_products','get_affected_products',{}),
   ('known_existing_details','get_cve_details',{'cve_id':'CVE-2024-0001'}),
   ('known_existing_relationships','explore_cve_relationships',{'cve_id':'CVE-2024-0001'}),
   ('missing_details','get_cve_details',{'cve_id':'CVE-2099-9999999999999999999'}),
  ]
  for label,tool,arguments in cases:
   call=request('mcpServer/tool/call',{'threadId':thread_id,'server':NAME,'tool':tool,'arguments':arguments})
   body=call.get('structuredContent')
   if not body:
    parts=[v.get('text','') for v in call.get('content',[]) if v.get('type')=='text']
    try:body=json.loads('\n'.join(parts))
    except ValueError:body={'message':'\n'.join(parts)[:1500]}
   out['functional_calls'][label]={'tool':tool,'arguments':arguments,'isError':bool(call.get('isError')),'result':body}
  out['status']='FUNCTIONAL_SUITE_EXECUTED_NOT_YET_ASSERTED'
 if args.call_readonly_stats and out['status']=='DISCOVERED_SIX':
  call=request('mcpServer/tool/call',{'threadId':thread_id,'server':NAME,'tool':'get_vulnerability_statistics','arguments':{}})
  assert not call.get('isError'), 'Read-only tool returned an error'
  stats=call.get('structuredContent')
  if not isinstance(stats,dict) or 'total_cves' not in stats:
   stats=json.loads(next(v['text'] for v in call.get('content',[]) if v.get('type')=='text'))
  assert stats.get('total_cves',0)>0
  out['readonly_tool_call']={'name':'get_vulnerability_statistics','status':'PASS','total_cves':stats.get('total_cves'),'as_of':stats.get('as_of')}
except Exception as exc:
 out['status']='PROBE_FAILED';out['exception_type']=type(exc).__name__
finally:
 if process.poll() is None:
  process.terminate()
  process.wait(timeout=10)
 out['stderr_error_labels']=labels[-30:]
destination=Path(__file__).with_name(args.evidence_name or ('native_discovery_'+args.binary+'.json'))
destination.write_text(json.dumps(out,indent=2),encoding='utf-8')
if args.comprehensive_baseline:
 print(json.dumps({'status':out['status'],'evidence':str(destination),'schemas_fields':{k:sorted(v['inputSchema'].get('properties',{})) for k,v in out.get('schemas',{}).items()},'calls':{k:{'isError':v['isError'],'structured':v['structuredContent_present'],'characters':v['content_characters'],'total':v['result'].get('total'),'items':len(v['result'].get('items',[]))} for k,v in out.get('baseline_calls',{}).items()}},indent=2))
elif args.functional_suite:
 print(json.dumps({'at':out['at'],'status':out['status'],'evidence':str(destination),'calls':{k:{'isError':v['isError'],'total':v['result'].get('total'),'items_count':len(v['result'].get('items',[])),'message':v['result'].get('message')} for k,v in out.get('functional_calls',{}).items()}},indent=2))
else:print(json.dumps(out,indent=2))
