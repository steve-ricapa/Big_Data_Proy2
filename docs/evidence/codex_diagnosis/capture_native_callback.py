"""Observe the native CLI authorize request without submitting user credentials.

The authorization URL stays in process memory. Only public configuration fields
are persisted. The native CLI may launch the default browser; no browser is
controlled, no credentials are read and the waiting CLI is terminated.
"""
import json
import argparse
import os
import queue
import re
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

NAME='big_data_ii_-_threat_intelligence'
BASE='https://ti-136-114-21-18.sslip.io/mcp'
binary=Path.home()/'AppData/Roaming/npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
home=Path(os.environ['LOCALAPPDATA'])/'Temp/opencode/codex-native-callback-20261111'
parser=argparse.ArgumentParser()
parser.add_argument('--effective',action='store_true')
args=parser.parse_args()
if args.effective:home=Path.home()/'.codex'
else:home.mkdir(parents=True,exist_ok=True)
config=home/'config.toml'
if not args.effective:assert not config.exists(),'Refuse to overwrite existing isolated config'
with socket.socket() as listener:
 listener.bind(('127.0.0.1',43219))
if not args.effective:config.write_text('mcp_oauth_callback_port = 43219\nmcp_oauth_callback_url = "http://127.0.0.1:43219/callback"\n[mcp_servers.'+NAME+']\nurl = "'+BASE+'"\nscopes = ["openid", "ti:read"]\n[mcp_servers.'+NAME+'.oauth]\nclient_id = "ti-codex"\n',encoding='utf-8')
p=subprocess.Popen([str(binary),'mcp','login',NAME,'--scopes','openid,ti:read'],env=dict(os.environ,CODEX_HOME=str(home)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
lines=queue.Queue()
def consume():
 for line in p.stdout:
  lines.put(line)
threading.Thread(target=consume,daemon=True).start()
out={'at':datetime.now(UTC).isoformat(),'version':subprocess.run([str(binary),'--version'],capture_output=True,text=True).stdout.strip(),'isolated_home':str(home),'credentials_submitted':False}
try:
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  try:line=lines.get(timeout=0.3)
  except queue.Empty:
   if p.poll() is not None:break
   continue
  for candidate in re.findall(r'https?://[^\s<>"\x1b]+',line):
   parts=urlsplit(candidate)
   query=parse_qs(parts.query)
   if 'redirect_uri' not in query:continue
   assert parts.hostname=='ti-136-114-21-18.sslip.io'
   out['authorization_endpoint']=parts.scheme+'://'+parts.netloc+parts.path
   out['request']={k:query[k][0] for k in ('client_id','redirect_uri','scope','response_type','code_challenge_method','resource') if k in query}
   out['pkce_challenge_present']=bool(query.get('code_challenge'))
   out['state_present']=bool(query.get('state'))
   break
  if 'request' in out:break
finally:
 if p.poll() is None:
  p.terminate()
  p.wait(timeout=10)
assert 'request' in out,'No native authorization URL observed; output suppressed'
assert out['request']['client_id']=='ti-codex'
assert out['request']['code_challenge_method']=='S256'
out['status']='PASS'
Path(__file__).with_name('effective_native_callback.json' if args.effective else 'native_callback.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
