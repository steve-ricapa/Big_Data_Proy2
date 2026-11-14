"""Read-only full parity, independent catalog, and source-volume measurements."""
import json
import subprocess

code=r'''
import hashlib,json
from datetime import UTC,datetime
from threat_intelligence.common.config import settings
from threat_intelligence.databases.mongodb import Mongo
from threat_intelligence.databases.cassandra import Cassandra
from threat_intelligence.databases.neo4j import Neo
config=settings();mongo=Mongo(config);cass=Cassandra(config,initialize_schema=False);neo=Neo(config)
def fingerprint(rows):
 total=0;seen=set();duplicates=0
 for identity,digest in rows:
  if identity in seen:duplicates+=1
  seen.add(identity)
  total=(total+int(hashlib.sha256((identity+':'+digest).encode()).hexdigest(),16))%(1<<256)
 return {'records':len(seen),'duplicate_ids':duplicates,'sha256_sum':f'{total:064x}'}
out={'at':datetime.now(UTC).isoformat(),'data_writes':False}
stage='fingerprints'
try:
 out['mongodb']=fingerprint((r['cve_id'],r['content_hash']) for r in mongo.collection.find({},{'_id':0,'cve_id':1,'content_hash':1}).batch_size(1000))
 out['cassandra']=fingerprint((r.cve_id,r.content_hash) for r in cass.session.execute('SELECT cve_id,content_hash FROM cves_by_id'))
 with neo.driver.session(database=neo.database) as session:
  out['neo4j']=fingerprint((r['id'],r['hash']) for r in session.run('MATCH(c:CVE) RETURN c.id AS id,c.content_hash AS hash'))
 assert out['mongodb']==out['cassandra']==out['neo4j']
 stage='control_documents'
 current=mongo.collection.find_one({'cve_id':'CVE-2021-44228'},{'_id':0})
 cr=cass.session.execute('SELECT content_hash,document FROM cves_by_id WHERE cve_id=%s',('CVE-2021-44228',)).one()
 assert cr and json.loads(cr.document)=={k:v for k,v in current.items() if k!='raw_cve'}
 out['control_cvss']={identifier:mongo.collection.find_one({'cve_id':identifier},{'_id':0,'cvss':1})['cvss'] for identifier in ('CVE-2021-44228','CVE-2024-0001')}
 stage='independent_catalog'
 rows=mongo.collection.aggregate([{'$unwind':'$products'},{'$group':{'_id':'$products.id','cves':{'$addToSet':'$cve_id'}}},{'$project':{'n':{'$size':'$cves'}}}],allowDiskUse=True,maxTimeMS=90000)
 pairs=sorted((r['_id'],r['n']) for r in rows)
 out['independent_catalog']={'total':len(pairs),'id_count_sha256':hashlib.sha256(json.dumps(pairs,separators=(',',':')).encode()).hexdigest(),'method':'Mongo unwind + addToSet(CVE ID), independent from API two-stage group'}
 stage='source_volume'
 size={'$bsonSize':{'$ifNull':['$raw_cve',{}]}}
 group={'_id':None,'records':{'$sum':1},'raw_bson_bytes':{'$sum':size},'average_raw_bson_bytes':{'$avg':size},'maximum_raw_bson_bytes':{'$max':size}}
 out['source_volume']=next(mongo.collection.aggregate([{'$group':group}],maxTimeMS=90000))
 stage='text_explain'
 plan=mongo.collection.find({'$text':{'$search':"'\"%_*()[];--"}},{'_id':0,'cve_id':1}).limit(1).explain()
 parsed=[]
 def walk(v):
  if isinstance(v,dict):
   if 'parsedTextQuery' in v:parsed.append(v['parsedTextQuery'])
   for item in v.values():walk(item)
  elif isinstance(v,list):
   for item in v:walk(item)
 walk(plan)
 out['special_keyword_parsed_query']=parsed
 stage='snapshot_parity'
 stats=mongo.db.kpis.find_one({'_id':'latest'},{'_id':0})
 saved=cass.session.execute("SELECT payload FROM kpi_snapshots WHERE snapshot_id='latest'").one()
 assert json.loads(saved.payload)==stats
 out['snapshot']={'as_of':stats['as_of'],'total_cves':stats['total_cves'],'unique_affected_products':stats['unique_affected_products'],'rejected_cves':stats['rejected_cves'],'severity':stats['severity']}
 out['status']='PASS_READ_ONLY_PARITY_AND_CATALOG'
except Exception as e:
 out.update(status='FAIL',failed_stage=stage,exception_type=type(e).__name__,error_code=getattr(e,'code',None))
finally:
 mongo.close();cass.close();neo.close()
print(json.dumps(out))
'''
p=subprocess.run(['docker','exec','threat-intelligence-api-1','python','-c',code],capture_output=True,text=True,timeout=360,check=False)
assert p.returncode==0,'Read-only database proof failed; raw output suppressed'
print(json.dumps(json.loads(p.stdout.splitlines()[-1])))
