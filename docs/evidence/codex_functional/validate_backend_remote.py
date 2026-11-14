"""Read-only semantic/source/graph/KPI verification of the production fix."""
import json
import subprocess
from datetime import UTC, datetime

code=r'''
import json,httpx
from threat_intelligence.common.config import settings
from threat_intelligence.databases.mongodb import Mongo
from threat_intelligence.databases.neo4j import Neo
from threat_intelligence.databases.cassandra import Cassandra
from threat_intelligence.transformations.normalize import normalize
from threat_intelligence.analytics import audit
config=settings()
def connect(engine):
 if engine=='mongodb':return Mongo(config)
 if engine=='neo4j':return Neo(config)
 if engine=='cassandra':return Cassandra(config,initialize_schema=False)
 raise ValueError('Unknown engine')
mongo=connect('mongodb');cass=connect('cassandra');neo=connect('neo4j')
try:
 row=mongo.collection.find_one({'cve_id':'CVE-2021-44228'},{'_id':0})
 expected=normalize({'cve':row['raw_cve']})
 assert row==expected
 assert row['content_hash']=='f511cfc4077364e056813387ae2de7b08e8b43ee30f236eec0f46fd99a17aa18'
 assert row['cvss']['version']=='3.1' and row['cvss']['score']==10.0
 assert any(p['vendor']=='apache' and p['product']=='log4j' for p in row['products'])
 c=cass.session.execute('SELECT content_hash,document FROM cves_by_id WHERE cve_id=%s',(row['cve_id'],)).one()
 assert c and c.content_hash==row['content_hash']
 assert json.loads(c.document)=={k:v for k,v in row.items() if k!='raw_cve'}
 identity=neo.query('MATCH (c:CVE {id:$id}) RETURN c.content_hash AS hash',id=row['cve_id'])
 assert len(identity)==1 and identity[0]['hash']==row['content_hash']
 types=neo.query('MATCH (c:CVE {id:$id})-[r]->() RETURN type(r) AS type,count(r) AS n',id=row['cve_id'])
 types={r['type']:r['n'] for r in types}
 assert types['AFFECTS']==len(row['products'])
 assert types['AFFECTS_CPE']==len(row['cpes'])
 assert types['REFERENCES']==len(row['references'])
 assert types['CLASSIFIED_AS']==len(row['cwes'])
 products=neo.query('MATCH (c:CVE {id:$id})-[:AFFECTS]->(p:Product) RETURN p.id AS id',id=row['cve_id'])
 assert {p['id'] for p in products}=={p['id'] for p in row['products']}
 cpes=neo.query('MATCH (c:CVE {id:$id})-[:AFFECTS_CPE]->(p:CPE) RETURN p.id AS id',id=row['cve_id'])
 assert {p['id'] for p in cpes}=={p['criteria'] for p in row['cpes']}
 assert 'description_text' in mongo.collection.index_information()
 with httpx.Client(base_url='http://127.0.0.1:8000',timeout=40) as api:
  checks={}
  for label,path in [('detail','/api/v1/vulnerabilities/CVE-2021-44228'),('products','/api/v1/vulnerabilities/CVE-2021-44228/products'),('graph','/api/v1/graph/cve/CVE-2021-44228'),('keyword','/api/v1/vulnerabilities?q=log4j&page_size=5'),('combined','/api/v1/vulnerabilities?q=log4j&severity=CRITICAL&cve_id=CVE-2021-44228'),('negative_combined','/api/v1/vulnerabilities?severity=LOW&cve_id=CVE-2021-44228')]:
   r=api.get(path);assert r.status_code==200;body=r.json()
   checks[label]={'status':r.status_code,'total':body.get('total'),'items_count':len(body.get('items',[]))}
   if label=='detail':assert body==row
   if label=='products':assert body['items']==row['products'] and body['cpes']==row['cpes']
   if label=='graph':
    assert body['total_relationships']==sum(types.values()) and body['truncated'] is True
    assert len(body['items'])==250
    assert any(v['relationship']=='AFFECTS' and v['entity']['id']=='["a","apache","log4j"]' for v in body['items'])
   if label=='keyword':assert body['total']==mongo.collection.count_documents({'$text':{'$search':'log4j'}})
   if label=='combined':assert body['total']==1
   if label=='negative_combined':assert body['total']==0
finally:
 mongo.close();cass.close();neo.close()
audit.connect=connect
audit_result=audit.audit_kpis()
print(json.dumps({'status':'PASS','direct_three_engine_hashes_match_source':True,'canonical_hash':row['content_hash'],'cvss':row['cvss'],'product_count':len(row['products']),'cpe_count':len(row['cpes']),'graph_relationship_counts':types,'api_checks':checks,'kpi_audit':audit_result}))
'''
p=subprocess.run(['docker','exec','threat-intelligence-api-1','python','-c',code],capture_output=True,text=True,timeout=360,check=False)
assert p.returncode==0,'Read-only semantic verification failed; raw output suppressed'
out=json.loads(p.stdout.splitlines()[-1]);out['at']=datetime.now(UTC).isoformat()
print(json.dumps(out))
