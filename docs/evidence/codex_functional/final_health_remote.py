"""Final read-only scheduling/health and sanitized post-deployment log summary."""
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from urllib.parse import urlsplit

out={'at':datetime.now(UTC).isoformat(),'logs_since':'2026-11-11T17:44:00Z','services':{}}
for service in ('api','mcp-remote','caddy','mongodb','cassandra','neo4j'):
 p=subprocess.run(['docker','logs','--since',out['logs_since'],'--tail','1000','threat-intelligence-'+service+'-1'],capture_output=True,text=True,check=False)
 statuses=Counter();errors=Counter()
 for line in (p.stdout+'\n'+p.stderr).splitlines():
  try:record=json.loads(line)
  except ValueError:record=None
  if service=='caddy' and isinstance(record,dict) and 'request' in record:
   path=urlsplit(record['request'].get('uri','')).path
   if path=='/mcp' or path.startswith('/.well-known/'):
    statuses[path+':'+str(record.get('status'))]+=1
  elif service=='api':
   match=re.search(r'"(?:GET|POST) ([^ ]+) HTTP/[^"]+" (\d{3})',line)
   if match:statuses[urlsplit(match[1]).path+':'+match[2]]+=1
  for error in re.findall(r'(?i)(Request failed|Traceback|ServiceUnavailable|Connection refused|ReadTimeout|503 Service Unavailable|500 Internal Server Error|InvalidAudienceError|InvalidIssuerError)',line):errors[error]+=1
 out['services'][service]={'log_read_exit':p.returncode,'http_counts':dict(statuses),'unexpected_error_labels':dict(errors)}
code="""
import json
from airflow.models import DagModel,DagRun
from airflow.utils.session import create_session
with create_session() as s:
 d=s.query(DagModel).filter_by(dag_id='nvd_threat_intelligence').one()
 print(json.dumps({'dag_active':not d.is_paused,'active_runs':s.query(DagRun).filter(DagRun.dag_id==d.dag_id,DagRun.state.in_(['queued','running'])).count()}))
"""
p=subprocess.run(['docker','exec','threat-intelligence-airflow3-scheduler-1','python','-c',code],capture_output=True,text=True,timeout=40,check=False)
assert p.returncode==0,'Read-only scheduler check failed; response suppressed'
out['scheduler']=json.loads(next(v for v in p.stdout.splitlines() if v.startswith('{')))
p=subprocess.run(['systemctl','is-active','ti-backup.service'],capture_output=True,text=True,check=False)
out['backup_active']=p.stdout.strip() in ('active','activating','reloading')
assert out['scheduler']['dag_active']
print(json.dumps(out))
