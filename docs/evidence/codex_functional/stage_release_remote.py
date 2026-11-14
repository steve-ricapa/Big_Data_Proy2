"""Stage allowlisted public source/data and build app-only release images."""
import base64
import hashlib
import json
import shutil
import subprocess
import zlib
from pathlib import Path

PAYLOAD = "__PUBLIC_PAYLOAD__"
RELEASE = "functional20261111"
ROOT = Path('/opt/threat-intelligence')
OUT = ROOT / 'docs/evidence/codex_functional'
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
allowed = {
    'services/api/app.py', 'services/mcp_server/server.py',
    'src/threat_intelligence/databases/mongodb/__init__.py',
    'scripts/cloud_backfill_log4shell.py',
    'data/raw/nvd/backfill/nvdcve-2.0-CVE-2021-44228.json',
}
assert set(data) == allowed
result = {'source_files': {}, 'images': {}, 'production_containers_recreated': False}
for name, encoded in data.items():
    target = ROOT / name
    assert target.resolve().is_relative_to(ROOT)
    content = base64.b64decode(encoded)
    backup = OUT / 'previous_sources' / name
    if target.exists():
        assert not backup.exists(), 'A prior stage exists; do not overwrite recovery copy'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.functional-tmp')
    temporary.write_bytes(content)
    temporary.replace(target)
    result['source_files'][name] = hashlib.sha256(content).hexdigest()
context = OUT / 'build'
context.mkdir(exist_ok=True)
for name in sorted(allowed):
    if name.startswith(('services/', 'src/')):
        dest = context / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
for kind, base in (('app', 'ti-app:local'), ('mcp', 'ti-mcp:local')):
    previous = 'ti-' + kind + ':pre-' + RELEASE
    subprocess.run(['docker', 'tag', base, previous], check=True)
    dockerfile = context / ('Dockerfile.' + kind)
    dockerfile.write_text('FROM ' + base + '\nUSER root\nCOPY services/ /app/services/\nCOPY src/ /app/src/\nUSER 10001:10001\n')
    tag = 'ti-' + kind + ':' + RELEASE
    with (OUT / ('build_' + kind + '.log')).open('w') as log:
        p = subprocess.run(['docker', 'build', '--pull=false', '-f', str(dockerfile), '-t', tag, str(context)], stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False)
    assert p.returncode == 0, 'App-only image build failed; production images untouched'
    image = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', tag], capture_output=True, text=True, check=True).stdout.strip()
    result['images'][kind] = {'tag': tag, 'previous_tag': previous, 'image_id': image}
result['status'] = 'STAGED_NOT_ACTIVATED'
(OUT / 'release_staged.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
