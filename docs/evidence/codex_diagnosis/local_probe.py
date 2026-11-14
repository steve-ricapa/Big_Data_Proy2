"""Inspect only relevant Codex config/log diagnostics; never read auth stores."""
import json
import os
import re
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
home=Path.home()
out={'at':datetime.now(UTC).isoformat(),'config':[],'extensions':[],'log_matches':[]}
homes={home/'.codex'}
if os.getenv('CODEX_HOME'):
    homes.add(Path(os.environ['CODEX_HOME']))
for path in [*(p/'config.toml' for p in homes), ROOT/'.codex/config.toml']:
    if not path.exists():continue
    try:d=tomllib.loads(path.read_text(encoding='utf-8'))
    except Exception:continue
    for name,server in d.get('mcp_servers',{}).items():
        if 'big_data' not in name.lower() and 'ti-136-114-21-18.sslip.io' not in str(server.get('url','')):continue
        oauth=server.get('oauth',{})
        out['config'].append({'file':str(path),'name':name,'url':server.get('url'),'enabled':server.get('enabled',True),'auth':server.get('auth'),'scopes':server.get('scopes'),'http_header_names':list(server.get('http_headers',{})),'bearer_env_var_configured':bool(server.get('bearer_token_env_var')),'oauth':{k:v for k,v in oauth.items() if k in ('client_id','callback_url','callback_port')},'oauth_client_secret_present':bool(oauth.get('client_secret')),'global_callback_port':d.get('mcp_oauth_callback_port'),'global_callback_url':d.get('mcp_oauth_callback_url')})
for base in (home/'.vscode/extensions',home/'.vscode-insiders/extensions'):
    if not base.exists():continue
    for directory in base.glob('openai.chatgpt-*'):
        try:p=json.loads((directory/'package.json').read_text(encoding='utf-8'))
        except Exception:continue
        binaries=list(directory.glob('**/codex.exe'))
        out['extensions'].append({'path':str(directory),'version':p.get('version'),'binaries':[str(p) for p in binaries]})
for extension in out['extensions']:
    for binary in extension['binaries']:
        p=subprocess.run([binary,'--version'],capture_output=True,text=True,timeout=20)
        extension['codex_version']=p.stdout.strip() if p.returncode==0 else 'unavailable'

def clean(text):
    text=re.sub(r'(?i)(bearer\s+)[^\s"\']+',r'\1[REDACTED]',text)
    text=re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[JWT_REDACTED]',text)
    text=re.sub(r'(?i)((?:access_token|refresh_token|id_token|client_secret|code_verifier|password|authorization|state|code)["\']?\s*[:=]\s*["\']?)[^\s&,"\'}]+',r'\1[REDACTED]',text)
    text=re.sub(r'(https?://[^\s?"\']+)\?[^\s"\']+',r'\1?[QUERY_REDACTED]',text)
    text=re.sub(r'(?i)(--oauth-client-secret\s+)[^\s]+',r'\1[REDACTED]',text)
    return text[:1800]

files=[]
for h in homes:
    if (h/'log').exists():files+=list((h/'log').glob('*.log'))
appdata=Path(os.environ.get('APPDATA',str(home/'AppData/Roaming')))
base=appdata/'Code/logs'
if base.exists():
    sessions=sorted((p for p in base.iterdir() if p.is_dir()),key=lambda p:p.stat().st_mtime,reverse=True)[:4]
    for session in sessions:
        files+=list(session.glob('**/*openai*/*.log'))+list(session.glob('**/*codex*/*.log'))+list(session.glob('**/exthost.log'))
for path in sorted(set(files),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
    try:
        with path.open('rb') as f:
            size=path.stat().st_size;f.seek(max(0,size-3_000_000));text=f.read().decode('utf-8',errors='replace')
    except OSError:continue
    for n,line in enumerate(text.splitlines()):
        if any(k in line for k in ('ToolCall:', '"tool_uses"', '"prompt"')):continue
        if ('big_data_ii' in line.lower() or 'ti-136-114-21-18.sslip.io' in line) and any(k in line.lower() for k in ('error','oauth','mcp','registration','401','403')):
            out['log_matches'].append({'file':str(path),'tail_line':n+1,'text':clean(line)})
out['log_matches']=out['log_matches'][-50:]
(ROOT/'docs/evidence/codex_diagnosis/local.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
