"""Import-only candidate check, no credentials mounted or network access."""
import json
import subprocess
code="""
import json
try:
 from services.mcp_server import server
 print(json.dumps({'import':'PASS'}))
except Exception as e:
 print(json.dumps({'import':'FAIL','type':type(e).__name__,'message':str(e)[:1400]}))
"""
p=subprocess.run(['docker','run','--rm','--network','none','--memory','256m','--entrypoint','python','ti-mcp:comprehensive20261111','-c',code],capture_output=True,text=True,check=False)
print(p.stdout)
