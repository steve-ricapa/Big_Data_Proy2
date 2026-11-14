"""Inspect secret mount flags and local health endpoints; no secret values."""
import json
import subprocess

def run(args):
    p=subprocess.run(args,capture_output=True,text=True)
    return p.stdout if p.returncode==0 else None

ids=run(['docker','ps','-q','--filter','label=com.docker.compose.project=threat-intelligence']).split()
out=[]
for c in json.loads(run(['docker','inspect',*ids])):
    out.append({'service':c['Config']['Labels']['com.docker.compose.service'], 'secret_mounts':[{'destination':m['Destination'],'read_write':m['RW']} for m in c['Mounts'] if m['Destination'].startswith('/run/secrets')]})
print(json.dumps({'mounts':out}))
