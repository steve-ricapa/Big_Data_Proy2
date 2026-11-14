"""Coordinate the explicitly bounded data correction; no service deployment."""
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

now=datetime.now(UTC)
assert not (1 <= now.hour <= 3), 'Too close to backup/ETL window; coordinate separately'
backup=subprocess.run(['systemctl','is-active','ti-backup.service'],capture_output=True,text=True,check=False)
assert backup.stdout.strip() not in ('active','activating','reloading'), 'Backup is active'
p=subprocess.run(['docker','exec','threat-intelligence-airflow3-scheduler-1','python','/opt/project/scripts/cloud_backfill_log4shell.py'],capture_output=True,text=True,timeout=900,check=False)
records=[]
for line in p.stdout.splitlines():
 try:records.append(json.loads(line))
 except ValueError:pass
out={'at':now.isoformat(),'backup_active':False,'exit':p.returncode,'records':records}
if p.returncode:
 out['exception_types']=re.findall(r'(?m)^([A-Za-z][A-Za-z0-9_]*(?:Error|Exception)):',p.stderr)
out_path=Path('/opt/threat-intelligence/docs/evidence/codex_functional/backfill_execution.json')
out_path.write_text(json.dumps(out,indent=2))
print(json.dumps(out))
assert p.returncode==0,'Backfill did not complete; inspect persisted stages before retry; no automatic data rollback'
