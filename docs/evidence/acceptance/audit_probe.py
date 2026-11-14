"""One-off acceptance audit: read-only VM/container/database probes."""
import hashlib
import json
import os
import stat
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/opt/threat-intelligence')


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        return {'error': 'command failed', 'returncode': p.returncode}
    return p.stdout


def inside(container, code):
    out = run(['docker', 'exec', container, 'python', '-c', code])
    if isinstance(out, dict):
        return out
    for line in reversed(out.splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            pass
    return {'error': 'no JSON response'}


result = {'at': datetime.now(UTC).isoformat()}
ids = run(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=threat-intelligence']).split()
containers = json.loads(run(['docker', 'inspect', *ids]))
result['docker'] = [{
    'service': c['Config']['Labels'].get('com.docker.compose.service'),
    'state': c['State']['Status'],
    'health': c['State'].get('Health', {}).get('Status', 'NO_HEALTHCHECK'),
    'ports': c['NetworkSettings']['Ports'],
    'image': c['Config']['Image'],
} for c in containers]
result['airflow'] = inside('threat-intelligence-airflow3-scheduler-1', '''
import json,airflow
from airflow.models import DagModel,DagRun,TaskInstance
from airflow.utils.session import create_session
def info(r):
 return {'run_id':r.run_id,'state':r.state,'start':str(r.start_date),'end':str(r.end_date),'duration_seconds':(r.end_date-r.start_date).total_seconds() if r.end_date and r.start_date else None}
with create_session() as s:
 d=s.query(DagModel).filter_by(dag_id='nvd_threat_intelligence').one()
 runs=s.query(DagRun).filter_by(dag_id=d.dag_id).order_by(DagRun.id.desc()).all()
 latest=next((r for r in runs if r.state=='success'),None)
 out={'version':airflow.__version__,'paused':d.is_paused,'active_runs':[info(r) for r in runs if r.state in ('running','queued')],'latest_run':info(runs[0]),'latest_success':info(latest) if latest else None}
 out['tasks']=[{'task':t.task_id,'state':t.state,'try':t.try_number,'duration_seconds':t.duration} for t in s.query(TaskInstance).filter_by(dag_id=d.dag_id,run_id=latest.run_id).all()] if latest else []
 print(json.dumps(out))
''')
if not result['airflow'].get('active_runs', [True]):
    result['databases'] = inside('threat-intelligence-airflow3-scheduler-1', '''
import json,hashlib
from threat_intelligence.pipeline import connect
from threat_intelligence.common.config import settings
from threat_intelligence.databases.cassandra import Cassandra
out={}
for name in ('mongodb','cassandra','neo4j'):
 sink=Cassandra(settings(),initialize_schema=False) if name=='cassandra' else connect(name)
 try:
  sink.ping()
  if name=='mongodb':
   rows=((r['cve_id'],r['content_hash']) for r in sink.collection.find({}, {'_id':0,'cve_id':1,'content_hash':1}).batch_size(500))
   extra={'unique_index':any(i.get('unique') and list(i['key'].items())==[('cve_id',1)] for i in sink.collection.list_indexes())}
  elif name=='cassandra':
   rows=((r.cve_id,r.content_hash) for r in sink.session.execute('SELECT cve_id,content_hash FROM cves_by_id'))
   extra={}
  else:
   rows=((r['id'],r['hash']) for r in sink.query('MATCH (c:CVE) RETURN c.id AS id,c.content_hash AS hash'))
   extra={'relationships':sink.query('MATCH ()-[r]->() RETURN count(r) AS n')[0]['n']}
  ids=set(); n=total=0
  for identifier,h in rows:
   ids.add(identifier);n+=1
   total=(total+int.from_bytes(hashlib.sha256((identifier+':'+h).encode()).digest(),'big'))%(1<<256)
  out[name]={'records':n,'unique':len(ids),'duplicate_ids':n-len(ids),'sha256_sum':f'{total:064x}',**extra}
 finally:sink.close()
print(json.dumps(out))
''')
else:
    result['databases'] = {'skipped': 'active pipeline; do not interfere'}
manifests=[]
for p in (ROOT/'data/staging').glob('*/run.json'):
    try:
        m=json.loads(p.read_text())
        if m.get('stages',{}).get('nvd_sync'):
            manifests.append((p.stat().st_mtime,m))
    except (ValueError,OSError):
        pass
result['latest_nvd_manifest']=max(manifests,key=lambda t:t[0])[1] if manifests else None
for name in ('backup_validation.json','cloud_backup_upload.json','backup_restore_validation.json'):
    p=ROOT/'docs/evidence'/name
    result[name]=json.loads(p.read_text()) if p.exists() else None
b=result.get('backup_validation.json')
if b:
    item=next(i for i in b['archives'] if i['file']=='mongodb_data.tar.gz')
    p=Path(b['directory'])/item['file']
    with p.open('rb') as stream:
        result['backup_archive_hash_matches']=hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
restore=result.get('backup_restore_validation.json')
if restore:
    out=run(['docker','inspect','--format','{{.State.Status}}',restore['restore_container']])
    result['restore_container_state']=out.strip() if isinstance(out,str) else out
result['secret_permissions']={
    'directory_mode':oct(stat.S_IMODE((ROOT/'secrets').stat().st_mode)),
    'world_readable_names':[p.name for p in (ROOT/'secrets').iterdir() if p.is_file() and p.stat().st_mode & stat.S_IROTH],
    'note':'Only permissions inspected; no contents emitted',
}
result['listeners']=run(['ss','-lnt'])
result['networks']=json.loads(run(['docker','network','inspect','threat-intelligence_data']))[0]['Internal']
result['timers']=run(['systemctl','list-timers','--all','--no-pager','ti-backup.timer','ti-health.timer'])
result['backup_service']=run(['systemctl','show','ti-backup.service','--property=Result,ExecMainStatus,ActiveState'])
print(json.dumps(result,default=str))
