"""Use deliberately wrong TOML types, without credentials, to detect parsed OAuth fields."""
import json,os,subprocess
from pathlib import Path
binary=Path.home()/'AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
home=Path(os.environ['LOCALAPPDATA'])/'Temp/opencode/codex-mcp-field-check'
home.mkdir(exist_ok=True)
out={}
for key,value in {'client_id':'123','client_secret':'123','callback_url':'123','callback_port':'"invalid-port"'}.items():
 (home/'config.toml').write_text('[mcp_servers.probe]\nurl="http://127.0.0.1:1/mcp"\n[mcp_servers.probe.oauth]\n'+key+'='+value+'\n',encoding='utf-8')
 p=subprocess.run([str(binary),'mcp','get','probe','--json'],env=dict(os.environ,CODEX_HOME=str(home)),capture_output=True,text=True,timeout=20)
 out[key]={'exit':p.returncode,'type_rejected':p.returncode!=0,'diagnostics':[s for s in p.stderr.splitlines() if any(x in s for x in ('invalid type','expected','oauth.',key))]}
for key,value in {'mcp_oauth_callback_url':'123','mcp_oauth_callback_port':'"invalid-port"'}.items():
 (home/'config.toml').write_text(key+'='+value+'\n[mcp_servers.probe]\nurl="http://127.0.0.1:1/mcp"\n',encoding='utf-8')
 p=subprocess.run([str(binary),'mcp','get','probe','--json'],env=dict(os.environ,CODEX_HOME=str(home)),capture_output=True,text=True,timeout=20)
 out[key]={'exit':p.returncode,'type_rejected':p.returncode!=0,'diagnostics':[s for s in p.stderr.splitlines() if any(x in s for x in ('invalid type','expected',key))]}
Path(__file__).with_name('config_fields.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
