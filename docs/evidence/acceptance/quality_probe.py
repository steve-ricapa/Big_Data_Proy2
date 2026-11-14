"""Read-only independent KPI reconciliation and source fingerprints."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/opt/threat-intelligence')
code = '''
import json
from datetime import datetime,timedelta
from threat_intelligence.pipeline import connect
s=connect('mongodb')
try:
 k=s.db.kpis.find_one({'_id':'latest'})
 c=s.collection
 severity={r['_id']:r['n'] for r in c.aggregate([{'$group':{'_id':'$severity','n':{'$sum':1}}}])}
 months={r['_id']:r['n'] for r in c.aggregate([{'$group':{'_id':'$month','n':{'$sum':1}}}])}
 unique=list(c.aggregate([{'$unwind':'$products'},{'$group':{'_id':'$products.id'}},{'$count':'n'}]))[0]['n']
 asof=datetime.fromisoformat(k['as_of'])
 checks={'total':c.count_documents({})==k['total_cves'],'severity':severity==k['severity'],'monthly':months==k['monthly'],'rejected':c.count_documents({'status':'Rejected'})==k['rejected_cves'],'unique_products':unique==k['unique_affected_products'],'modified_30d':c.count_documents({'last_modified':{'$gte':(asof-timedelta(days=30)).isoformat(),'$lte':asof.isoformat()}})==k['modified_last_30_days']}
 print(json.dumps({'snapshot_at':k['as_of'],'independent_checks':checks,'total':k['total_cves'],'unique_products':unique}))
finally:s.close()
'''
p=subprocess.run(['docker','exec','threat-intelligence-airflow3-scheduler-1','python','-c',code],capture_output=True,text=True)
out={'kpi': json.loads(p.stdout.splitlines()[-1]) if p.returncode==0 else {'error':'KPI query failed'}}
out['source_hashes']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','services','tests') for p in (root/folder).rglob('*.py') if '__pycache__' not in p.parts}
print(json.dumps(out))
