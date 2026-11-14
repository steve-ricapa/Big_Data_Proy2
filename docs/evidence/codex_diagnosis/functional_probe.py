"""Read-only direct API and database diagnosis. No secrets/raw logs emitted."""
import json
import re
import subprocess
from datetime import UTC, datetime

code=r'''
import json,httpx,traceback
from threat_intelligence.common.config import settings
from threat_intelligence.databases.mongodb import Mongo
from threat_intelligence.databases.neo4j import Neo
from threat_intelligence.databases.cassandra import Cassandra
config=settings();mongo=Mongo(config);neo=Neo(config);cass=Cassandra(config,initialize_schema=False)
out={'api':{},'databases':{},'sample':{}}
ids=['CVE-2021-44228']
sample=mongo.collection.find_one({'products.0':{'$exists':True},'cvss':{'$ne':None}},{'_id':0,'cve_id':1,'cvss':1,'products':1,'description':1})
assert sample
out['sample']={k:sample[k] for k in ('cve_id','cvss','products')};ids.append(sample['cve_id'])
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=40) as c:
 for identifier in ids:
  for suffix,path in [('search','/api/v1/vulnerabilities?cve_id='+identifier),('detail','/api/v1/vulnerabilities/'+identifier),('graph','/api/v1/graph/cve/'+identifier)]:
   r=c.get(path)
   try:body=r.json()
   except ValueError:body={'not_json':True}
   out['api'][identifier+':'+suffix]={'status':r.status_code,'body':body}
 for label,path in [('ready','/ready'),('stats','/api/v1/kpis'),('keyword','/api/v1/vulnerabilities?q=log4j'),('severity','/api/v1/vulnerabilities?severity=CRITICAL&page_size=1')]:
  r=c.get(path);body=r.json()
  if label=='keyword':body={'total':body.get('total'),'first_ids':[v['cve_id'] for v in body.get('items',[])[:3]],'q_appears_ignored':True}
  out['api'][label]={'status':r.status_code,'body':body}
for identifier in ids:
 m=mongo.collection.find_one({'cve_id':identifier},{'_id':0,'cve_id':1,'content_hash':1,'cvss':1,'products':1})
 c=cass.session.execute('SELECT cve_id,content_hash,document FROM cves_by_id WHERE cve_id=%s',(identifier,)).one()
 try:
  n=neo.query('MATCH (c:CVE {id:$id}) OPTIONAL MATCH (c)-[r]->() RETURN c.id AS id,c.content_hash AS hash,count(r) AS relationships',id=identifier)
  graph={'found':bool(n),'rows':n}
 except Exception as e:
  graph={'exception_type':type(e).__name__,'code':getattr(e,'code',None)}
 out['databases'][identifier]={'mongodb':{'found':m is not None,'row':m},'cassandra':{'found':c is not None,'content_hash':c.content_hash if c else None},'neo4j':graph}
out['mongodb_total']=mongo.collection.count_documents({},hint='cve_id_1')
mongo.close();neo.close();cass.close()
print(json.dumps(out))
'''
p=subprocess.run(['docker','exec','threat-intelligence-api-1','python','-c',code],capture_output=True,text=True,timeout=180,check=False)
assert p.returncode==0,'Functional read-only probe failed; raw output suppressed'
out=json.loads(p.stdout.splitlines()[-1]);out['at']=datetime.now(UTC).isoformat()
out['logs']={}
for service in ('mcp-remote','api','caddy','mongodb','cassandra','neo4j'):
 p=subprocess.run(['docker','logs','--since','2h','--tail','700','threat-intelligence-'+service+'-1'],capture_output=True,text=True,check=False)
 matches=[]
 for line in (p.stdout+'\n'+p.stderr).splitlines():
  labels=re.findall(r'(?i)(HTTPStatusError|RuntimeError|KeyError|TypeError|ValueError|SyntaxError|ClientError|ServiceUnavailable|Unauthorized|Forbidden|invalid_token|CVE not found|Request failed|Connection refused|timed out|404 Not Found|503 Service Unavailable|401 Unauthorized|403 Forbidden)',line)
  if labels:matches.append(labels)
 out['logs'][service]={'read_exit':p.returncode,'error_labels':matches[-30:]}
print(json.dumps(out))
