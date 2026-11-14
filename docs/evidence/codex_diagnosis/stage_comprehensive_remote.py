"""Stage/build a bounded application candidate; no activation or data writes."""
import ast
import base64
import hashlib
import json
import shutil
import subprocess
import zlib
from pathlib import Path

PAYLOAD='__PUBLIC_PAYLOAD__'
ROOT=Path('/opt/threat-intelligence')
OUT=ROOT/'docs/evidence/mcp_comprehensive'
OUT.mkdir(parents=True,exist_ok=True)
context=OUT/'candidate'
context.mkdir(exist_ok=False)
files=json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
expected={'services/api/app.py','services/api/views.py','services/mcp_server/server.py','services/mcp_server/contracts.py','services/mcp_server/remote.py'}
assert set(files)==expected
before={'services/api/app.py':'f26f4761516707a207c0b5e51e40a5a5c9ea367b96461ea926d0810851beed49','services/mcp_server/server.py':'54d11f86ec8b26f5d0c3e03b86be5ba2b2a6e2cf13e19822ec3515de2156de05','services/mcp_server/remote.py':'0b240c28779f06bfe5b8b1ad51225a1517b49b0174fb4efd5fa1c65d9b627c8f'}
for name,digest in before.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Production source drift: review before overwriting'
for name in expected-before.keys():assert not (ROOT/name).exists(),'New filename is already user work; review'
for name,encoded in files.items():
 path=context/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(encoded))
def security_nodes(path):
 tree=ast.parse(path.read_text())
 return [ast.dump(node,include_attributes=False) for node in ast.walk(tree) if isinstance(node,ast.ClassDef) and node.name=='OIDCVerifier' or isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('AuthSettings','TransportSecuritySettings')]
assert security_nodes(ROOT/'services/mcp_server/remote.py')==security_nodes(context/'services/mcp_server/remote.py'),'OAuth/security logic changed'
images={}
for kind in ('app','mcp'):
 base='ti-'+kind+':local';backup='ti-'+kind+':pre-comprehensive20261111';tag='ti-'+kind+':comprehensive20261111'
 subprocess.run(['docker','tag',base,backup],check=True)
 dockerfile=context/('Dockerfile.'+kind)
 dockerfile.write_text('FROM '+base+'\nUSER root\nCOPY services/ /app/services/\nUSER 10001:10001\n')
 with (OUT/('build_'+kind+'.log')).open('w') as log:
  p=subprocess.run(['docker','build','--pull=false','-f',str(dockerfile),'-t',tag,str(context)],stdout=log,stderr=subprocess.STDOUT,timeout=600,check=False)
 assert p.returncode==0,'Candidate image build failed; production unchanged'
 images[kind]={'candidate':tag,'rollback':backup}
result={'status':'STAGED_NOT_ACTIVATED','files':{name:hashlib.sha256((context/name).read_bytes()).hexdigest() for name in expected},'images':images,'oauth_verifier_and_security_settings_ast_unchanged':True,'production_sources_changed':False,'data_writes':False}
(OUT/'stage.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
