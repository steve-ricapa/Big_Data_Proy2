"""Restore the cloud cold Mongo backup into an isolated volume, never the source.

Expected fingerprint comes from the latest successful verify stage in
data/staging/*/run.json, so it stays valid after incremental NVD syncs.
"""

import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/opt/threat-intelligence")


def run(args):
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True).stdout


def expected_fingerprint():
    manifests = []
    for path in (ROOT / "data/staging").glob("*/run.json"):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stage = manifest.get("stages", {}).get("verify")
        if stage and stage.get("fingerprints", {}).get("mongodb"):
            manifests.append((path.stat().st_mtime, manifest["run_dir"], stage))
    assert manifests, "No completed verify stage found in data/staging"
    _, run_dir, stage = max(manifests)
    return run_dir, stage["fingerprints"]["mongodb"]


def main():
    backup = json.loads((ROOT / "docs/evidence/backup_validation.json").read_text(encoding="utf-8"))
    assert backup["status"] == "SUCCESS"
    item = next(row for row in backup["archives"] if row["volume"].endswith("_mongodb_data"))
    archive = Path(backup["directory"]) / item["file"]
    with archive.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]
    run_id, expected = expected_fingerprint()
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%S").lower()
    volume, container = "ti-restore-mongo-" + suffix, "ti-restore-mongo-" + suffix
    run(["docker", "volume", "create", "--label", "ti.purpose=isolated-restore", volume])
    code = "import tarfile;\nwith tarfile.open('/backup/'+'" + item["file"] + "','r:gz') as t: t.extractall('/restore',filter='data')"
    run(["docker", "run", "--rm", "--user", "0:0", "--network", "none", "--mount", f"type=volume,source={volume},target=/restore", "--mount", f"type=bind,source={archive.parent},target=/backup,readonly", "--entrypoint", "python", "ti-app:local", "-c", code])
    run(["docker", "run", "-d", "--name", container, "--label", "ti.purpose=isolated-restore", "--network", "none", "--memory", "768m", "--mount", f"type=volume,source={volume},target=/data/db", "mongo:8.0.12", "mongod", "--dbpath", "/data/db/data", "--auth", "--bind_ip", "127.0.0.1", "--wiredTigerCacheSizeGB", "0.25"])
    try:
        ready = False
        for _ in range(60):
            try:
                run(["docker", "exec", container, "mongosh", "--quiet", "--eval", "quit(db.adminCommand('ping').ok ? 0 : 1)"])
                ready = True
                break
            except subprocess.CalledProcessError:
                time.sleep(2)
        assert ready, "Restored Mongo did not start"
        code = """import hashlib,json
from pathlib import Path
from pymongo import MongoClient
password=Path('/run/secrets/root-password').read_text().strip()
with MongoClient('mongodb://127.0.0.1:27017',username='ti_admin',password=password,authSource='admin') as client:
 total=n=0
 for r in client.threat_intelligence.cves.find({}, {'_id':0,'cve_id':1,'content_hash':1}):
  total=(total+int.from_bytes(hashlib.sha256((r['cve_id']+':'+r['content_hash']).encode()).digest(),'big'))%(1<<256);n+=1
 print(json.dumps({'records':n,'sha256_sum':f'{total:064x}'}))
"""
        output = run(["docker", "run", "--rm", "--network", f"container:{container}", "--mount", f"type=bind,source={ROOT / 'secrets/mongodb-root-password'},target=/run/secrets/root-password,readonly", "--entrypoint", "python", "ti-app:local", "-c", code])
        restored = json.loads(output)
        assert restored == expected, "Restored content fingerprint differs from latest verify stage"
        result = {"at": datetime.now(UTC).isoformat(), "status": "SUCCESS", "archive": str(archive), "sha256_valid": True, "source_volume_untouched": True, "restore_volume": volume, "restore_container": container, "network": "none", "expected_from_run": run_id, "restored": restored, "matches_latest_verify_fingerprint": True}
        (ROOT / "docs/evidence/backup_restore_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
    finally:
        run(["docker", "stop", "--time", "60", container])
        # Keep the isolated volume/container stopped for inspection; no source deletions.


if __name__ == "__main__":
    main()
