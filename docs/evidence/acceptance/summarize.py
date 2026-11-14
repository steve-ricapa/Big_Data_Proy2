"""Write local audit evidence index, not a production operation."""
import hashlib
import json
import socket
from datetime import UTC, datetime
from pathlib import Path

base=Path('docs/evidence/acceptance')
vm=json.loads((base/'vm_probe.json').read_text())
cloud=json.loads((base/'gcp_inventory.json').read_text())
out={'at':datetime.now(UTC).isoformat()}
out['tcp_probes']={}
for port in (443,27017,9042,7687,18081):
    try:
        with socket.create_connection(('136.114.21.18',port),timeout=3):
            out['tcp_probes'][str(port)]='reachable'
    except OSError:
        out['tcp_probes'][str(port)]='not reachable from auditor'
objects={o['name']:o for o in cloud['backup_objects']}
uploads=vm['cloud_backup_upload.json']['objects']
out['backup_gcs_metadata_match']=all(i['object'] in objects and int(objects[i['object']]['size'])==i['bytes'] and objects[i['object']].get('metadata',{}).get('sha256')==i['sha256'] for i in uploads)
out['backup_gcs_objects']=len(uploads)
quality=json.loads((base/'quality.json').read_text())
out['source_differences']=[n for n,h in quality['source_hashes'].items() if not Path(n).exists() or hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h]
paths=['docs/report/technical_report.md','docs/report/demo_script.md','docs/architecture/system.md','docs/architecture/data_flow.md','docs/architecture/gcp_deployed_architecture.md','docs/implementation/requirements.md','docs/evidence/crud.json','docs/evidence/screenshot_checklist.md']
out['academic_documents']={p:{'exists':Path(p).exists(),'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in paths}
out['document_discrepancies']=['system.md says no GCP resources applied','requirements.md says 42 tests, plan not applied, cloud awaiting authorization','technical_report.md mixes no automatic download (section 4) with implemented sync (sections 16-19)','reports claim 7 alert policies and 9 secrets; current API lists 5 and 10']
out['estimated_cost']={'usd_day':4.0804,'usd_30_days':round(4.0804*30,2),'usd_day_20pct':round(4.0804*1.2,4),'basis':'new VM/disks/IP/storage inventory and current official CPU/RAM/pd-balanced SKUs; variable service and egress reserves, not invoice'}
(base/'summary.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
