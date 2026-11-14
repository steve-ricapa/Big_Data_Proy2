"""Check installed config support using non-secret placeholders in isolated homes."""
import json,os,subprocess
from pathlib import Path
binary=Path.home()/'AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
home=Path(os.environ['LOCALAPPDATA'])/'Temp/opencode/codex-mcp-config-compatibility'
home.mkdir(parents=True,exist_ok=True)
config=home/'config.toml'
assert not config.exists(),'Choose a fresh isolated directory'
config.write_text('[mcp_servers.ti_diagnosis]\nurl="https://ti-136-114-21-18.sslip.io/mcp"\n[mcp_servers.ti_diagnosis.oauth]\nclient_id="ti-codex-proposed-not-created"\nclient_secret="NONSECRET_COMPATIBILITY_SENTINEL"\ncallback_url="http://127.0.0.1:43219/callback"\ncallback_port=43219\n',encoding='utf-8')
p=subprocess.run([str(binary),'mcp','get','ti_diagnosis','--json'],env=dict(os.environ,CODEX_HOME=str(home)),capture_output=True,text=True,timeout=30)
out={'exit':p.returncode,'config_parse_warnings':p.stderr.replace('NONSECRET_COMPATIBILITY_SENTINEL','[sentinel]'),'get':json.loads(p.stdout) if p.returncode==0 else None}
if out['get'] and 'oauth' in out['get']:
 out['get']['oauth'].pop('client_secret',None)
Path(__file__).with_name('compatibility.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
