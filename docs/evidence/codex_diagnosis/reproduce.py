"""Run actual installed Codex against isolated config; suppress auth URLs and secrets."""
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

base=Path(__file__).resolve().parent
binary=Path.home()/'AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
home=Path(os.environ['LOCALAPPDATA'])/'Temp/opencode/codex-mcp-diagnosis'
home.mkdir(parents=True,exist_ok=True)
config=home/'config.toml'
assert not config.exists() or config.read_text(encoding='utf-8')=='[mcp_servers.ti_diagnosis]\nurl = "https://ti-136-114-21-18.sslip.io/mcp"\n', 'Unexpected isolated config'
config.write_text('[mcp_servers.ti_diagnosis]\nurl = "https://ti-136-114-21-18.sslip.io/mcp"\n',encoding='utf-8')
env=dict(os.environ,CODEX_HOME=str(home))
out={'at':datetime.now(UTC).isoformat(),'isolated_home':str(home),'version':subprocess.run([str(binary),'--version'],capture_output=True,text=True).stdout.strip()}
try:
 p=subprocess.run([str(binary),'mcp','login','ti_diagnosis','--scopes','ti:read'],env=env,capture_output=True,text=True,timeout=45)
 out['exit']=p.returncode
 # Auth URLs/parameters are intentionally never written to evidence.
 text=p.stdout+'\n'+p.stderr
 text=re.sub(r'https?://[^\s"<>]+','[URL suppressed]',text)
 out['diagnostic_lines']=[line[:600] for line in text.splitlines() if not any(k in line.lower() for k in ('client_secret','access_token','refresh_token','code_verifier','state='))][-20:]
except subprocess.TimeoutExpired:
 out['timeout']=True
(base/'reproduction.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
