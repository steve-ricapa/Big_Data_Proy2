"""Restore cold archives into isolated scratch volumes, one engine at a time.

No public ports, no production volume mounts, no paid infrastructure. Scratch
containers are stopped on every exit; their labelled volumes remain inspectable.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/opt/threat-intelligence")
OUT = ROOT / "docs/evidence/acceptance_v2/restore_three.json"


def run(args, timeout=600):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        # Do not emit logs/arguments: database clients can contain credentials.
        raise RuntimeError(f"Isolated operation failed: {args[0]} (exit {p.returncode})")
    return p.stdout


CLIENT = r'''
import hashlib,json,socket,time,sys
from pathlib import Path
engine=sys.argv[1]
port={'mongodb':27017,'cassandra':9042,'neo4j':7687}[engine]
for _ in range(90):
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=2):pass
  break
 except OSError:time.sleep(2)
else:raise TimeoutError('isolated database listener not ready')
if engine=='mongodb':
 from pymongo import MongoClient
 client=MongoClient('mongodb://127.0.0.1:27017',username='ti_admin',password=Path('/run/secrets/password').read_text().strip(),authSource='admin',serverSelectionTimeoutMS=15000)
 rows=((r['cve_id'],r['content_hash']) for r in client.threat_intelligence.cves.find({}, {'_id':0,'cve_id':1,'content_hash':1}))
 close=client.close
elif engine=='cassandra':
 from cassandra.auth import PlainTextAuthProvider
 from cassandra.cluster import Cluster
 cluster=Cluster(['127.0.0.1'],auth_provider=PlainTextAuthProvider('ti_pipeline',Path('/run/secrets/password').read_text().strip()),connect_timeout=15)
 for _ in range(20):
  try:session=cluster.connect('threat_intelligence');break
  except Exception:time.sleep(3)
 else:raise RuntimeError('isolated Cassandra session unavailable')
 session.default_fetch_size=1000
 session.default_timeout=60
 rows=((r.cve_id,r.content_hash) for r in session.execute('SELECT cve_id,content_hash FROM cves_by_id'))
 close=cluster.shutdown
else:
 from neo4j import GraphDatabase
 driver=GraphDatabase.driver('bolt://127.0.0.1:7687',auth=None)
 session=driver.session(database='neo4j')
 rows=((r['id'],r['hash']) for r in session.run('MATCH (c:CVE) RETURN c.id AS id,c.content_hash AS hash'))
 close=driver.close
total=n=0; ids=set()
try:
 for identifier,h in rows:
  n+=1;ids.add(identifier)
  total=(total+int.from_bytes(hashlib.sha256((identifier+':'+h).encode()).digest(),'big'))%(1<<256)
 out={'records':n,'unique':len(ids),'sha256_sum':f'{total:064x}'}
 if engine=='neo4j':out['relationships']=session.run('MATCH ()-[r]->() RETURN count(r) AS n').single()['n']
 print(json.dumps(out))
finally:close()
'''


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    assert shutil.disk_usage("/srv/ti-data").free > 12 * 1024**3, "Need 12 GiB free for scratch"
    available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")))
    assert available > 4 * 1024**2, "Need 4 GiB available memory"
    active = run(["systemctl", "show", "ti-backup.service", "--property=ActiveState", "--value"]).strip()
    assert active not in ("active", "activating"), "Backup in progress"
    guard = "from airflow.models import DagRun;from airflow.utils.session import create_session;\nwith create_session() as s: assert s.query(DagRun).filter(DagRun.state.in_(['running','queued'])).count()==0"
    run(["docker", "exec", "threat-intelligence-airflow3-scheduler-1", "python", "-c", guard])
    backup = json.loads((ROOT / "docs/evidence/backup_validation.json").read_text())
    assert backup["status"] == "SUCCESS"
    # Bind the expected state to a completed verify BEFORE this cold backup,
    # never to a later scheduled synchronization.
    candidates = []
    backup_started = datetime.fromisoformat(backup["started_at"]).timestamp()
    for path in (ROOT / "data/staging").glob("*/run.json"):
        manifest = json.loads(path.read_text())
        verify = manifest.get("stages", {}).get("verify")
        if verify and path.stat().st_mtime <= backup_started:
            values = list(verify["fingerprints"].values())
            assert all(value == values[0] for value in values)
            candidates.append((path.stat().st_mtime, values[0]))
    assert candidates, "No verified pre-backup fingerprint available"
    expected = max(candidates, key=lambda pair: pair[0])[1]
    result = {"started_at": datetime.now(UTC).isoformat(), "backup": backup["directory"], "status": "IN_PROGRESS", "network": "none", "production_volumes_mounted": False, "engines": {}}
    source_directory = Path(backup["directory"])
    result["source"] = "local-cloud-archive"
    if "--gcs" in sys.argv:
        # Same-region private object downloads, bounded within the existing disk.
        bucket = "proyectobigdata2-514216-ti-dev-processed"
        source_directory = Path("/srv/ti-data/restore-downloads") / datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        source_directory.mkdir(parents=True, mode=0o700)
        source_directory.chmod(0o700)
        request = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(request, timeout=15) as response:
            token = json.load(response)["access_token"]
        result.update(source="private-gcs-download", bucket=bucket, download_directory=str(source_directory), downloaded=[])
        for item in backup["archives"]:
            if item["file"] not in ("mongodb_data.tar.gz", "cassandra_data.tar.gz", "neo4j_data.tar.gz"):
                continue
            key = f"backups/{Path(backup['directory']).name}/{item['file']}"
            url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{urllib.parse.quote(key, safe='')}?alt=media"
            request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
            path = source_directory / item["file"]
            with urllib.request.urlopen(request, timeout=90) as response, path.open("xb") as stream:
                while block := response.read(8 * 1024 * 1024):
                    stream.write(block)
            path.chmod(0o600)
            assert path.stat().st_size == item["bytes"]
            with path.open("rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]
            result["downloaded"].append({"object": key, "bytes": item["bytes"], "sha256_valid": True})
    OUT.write_text(json.dumps(result, indent=2))
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S").lower()
    for engine, image in (("mongodb", "mongo:8.0.12"), ("cassandra", "cassandra:4.1.9"), ("neo4j", "neo4j:5.26.12-community")):
        item = next(i for i in backup["archives"] if i["file"] == engine + "_data.tar.gz")
        archive = source_directory / item["file"]
        with archive.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"]
        name = f"ti-v2-restore-{engine}-{stamp}"
        run(["docker", "volume", "create", "--label", "ti.purpose=acceptance-v2-isolated-restore", name])
        extract = "import tarfile;from pathlib import PurePosixPath;\nwith tarfile.open('/backup/" + item["file"] + "','r:gz') as t:\n for m in t:\n  parts=PurePosixPath(m.name).parts\n  assert parts[0]=='data'\n  m.name=str(PurePosixPath(*parts[1:])) if len(parts)>1 else '.'\n  t.extract(m,'/restore',filter='data')"
        run(["docker", "run", "--rm", "--network", "none", "--user", "0:0", "--mount", f"type=volume,source={name},target=/restore", "--mount", f"type=bind,source={archive.parent},target=/backup,readonly", "--entrypoint", "python", "ti-app:local", "-c", extract])
        destination = {"mongodb": "/data/db", "cassandra": "/var/lib/cassandra", "neo4j": "/data"}[engine]
        command = ["docker", "run", "-d", "--name", name, "--hostname", "ti-restore", "--add-host", "ti-restore:127.0.0.1", "--label", "ti.purpose=acceptance-v2-isolated-restore", "--network", "none", "--memory", "2g", "--mount", f"type=volume,source={name},target={destination}"]
        if engine == "mongodb":
            command += [image, "mongod", "--auth", "--bind_ip", "127.0.0.1", "--wiredTigerCacheSizeGB", "0.25"]
        elif engine == "cassandra":
            source = json.loads(run(["docker", "inspect", "threat-intelligence-cassandra-1"]))[0]
            for variable in source["Config"]["Env"]:
                if variable.split("=", 1)[0] in ("CASSANDRA_CLUSTER_NAME", "CASSANDRA_DC", "CASSANDRA_RACK", "CASSANDRA_ENDPOINT_SNITCH"):
                    command += ["-e", variable]
            for variable in ("MAX_HEAP_SIZE=768M", "HEAP_NEWSIZE=128M", "CASSANDRA_LISTEN_ADDRESS=127.0.0.1", "CASSANDRA_BROADCAST_ADDRESS=127.0.0.1", "CASSANDRA_RPC_ADDRESS=127.0.0.1", "CASSANDRA_SEEDS=127.0.0.1"):
                command += ["-e", variable]
            command += ["--mount", f"type=bind,source={ROOT / 'scripts/cassandra-secure-entrypoint.sh'},target=/secure-entrypoint.sh,readonly", "--entrypoint", "/bin/bash", image, "/secure-entrypoint.sh", "cassandra", "-f"]
        else:
            for variable in ("NEO4J_AUTH=none", "NEO4J_server_memory_heap_initial__size=256m", "NEO4J_server_memory_heap_max__size=512m", "NEO4J_server_memory_pagecache_size=128m"):
                command += ["-e", variable]
            command += [image]
        try:
            run(command)
            client = ["docker", "run", "--rm", "--name", name + "-client", "--label", "ti.purpose=acceptance-v2-restore-client", "--memory", "512m", "--network", f"container:{name}"]
            if engine != "neo4j":
                secret = "mongodb-root-password" if engine == "mongodb" else "cassandra-writer-password"
                client += ["--mount", f"type=bind,source={ROOT / 'secrets' / secret},target=/run/secrets/password,readonly"]
            output = run([*client, "--entrypoint", "python", "ti-app:local", "-c", CLIENT, engine], timeout=360)
            actual = json.loads(output.splitlines()[-1])
            assert actual["records"] == actual["unique"] == expected["records"]
            assert actual["sha256_sum"] == expected["sha256_sum"]
            result["engines"][engine] = {"status": "PASS", "archive_sha256_valid": True, "restored": actual, "container": name, "scratch_volume": name}
        except Exception as error:
            result["engines"][engine] = {"status": "FAIL", "error_type": type(error).__name__, "container": name, "scratch_volume": name}
        finally:
            # Only this invocation's disposable client; never source data volumes.
            subprocess.run(["docker", "rm", "-f", name + "-client"], capture_output=True, timeout=30)
            subprocess.run(["docker", "stop", "--time", "90", name], capture_output=True, timeout=120)
            OUT.write_text(json.dumps(result, indent=2))
    result["status"] = "PASS" if len(result["engines"]) == 3 and all(e["status"] == "PASS" for e in result["engines"].values()) else "PARTIAL"
    result["finished_at"] = datetime.now(UTC).isoformat()
    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 1


def coordinated_main():
    container = "threat-intelligence-airflow3-scheduler-1"
    probe = "from airflow.models import DagModel;from airflow.utils.session import create_session;\nwith create_session() as s: print('PAUSED' if s.query(DagModel).filter_by(dag_id='nvd_threat_intelligence').one().is_paused else 'ACTIVE')"
    previous = run(["docker", "exec", container, "python", "-c", probe]).strip().splitlines()[-1]
    run(["docker", "exec", container, "airflow", "dags", "pause", "nvd_threat_intelligence"])
    try:
        return main()
    finally:
        if previous == "ACTIVE":
            run(["docker", "exec", container, "airflow", "dags", "unpause", "nvd_threat_intelligence"])


if __name__ == "__main__":
    raise SystemExit(coordinated_main())
