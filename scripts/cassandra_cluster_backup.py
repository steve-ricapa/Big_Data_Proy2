"""Take a pre-cutover Cassandra-only cold backup and restore it in isolation.

Run on the primary host as root with the DAG paused and no writers. Does not
change replication or mount the live volume in the scratch database.
"""

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from cloud_backup import upload
from cloud_restore_three import CLIENT

ROOT = Path("/opt/threat-intelligence")
PRIMARY = "threat-intelligence-cassandra-1"
VOLUME = "threat-intelligence_cassandra_data"
IMAGE = "cassandra:4.1.9"


def run(*args, **options):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, **options).stdout.strip()


def main():
    stamp = datetime.now(UTC).strftime("%Y%m%dt%H%M%S")
    directory = Path("/srv/ti-data/cassandra-migration") / stamp
    if len(sys.argv) == 2:
        previous = Path(sys.argv[1]).resolve()
        assert previous.parent == directory.parent and (previous / "cassandra.tar.gz").is_file()
        restore(previous, stamp, (previous / "snapshot.txt").read_text() if (previous / "snapshot.txt").exists() else f"pre-cluster-{previous.name}")
        return
    directory.mkdir(parents=True, mode=0o700)
    guard = """from airflow.models import DagModel, DagRun
from airflow.utils.session import create_session
with create_session() as s:
 assert s.query(DagModel).filter_by(dag_id='nvd_threat_intelligence').one().is_paused
 assert s.query(DagRun).filter(DagRun.state.in_(['running','queued'])).count()==0
"""
    run("docker", "exec", "threat-intelligence-airflow3-scheduler-1", "python", "-c", guard)
    if run("systemctl", "show", "ti-backup.service", "--property=ActiveState", "--value") != "inactive":
        raise RuntimeError("Daily backup not idle")
    archive = directory / "cassandra.tar.gz"
    (directory / "cassandra.yaml").write_text(run("docker", "exec", PRIMARY, "cat", "/etc/cassandra/cassandra.yaml"))
    (directory / "cassandra-rackdc.properties").write_text(run("docker", "exec", PRIMARY, "cat", "/etc/cassandra/cassandra-rackdc.properties"))
    schema = "from threat_intelligence.common.config import settings; from threat_intelligence.databases.cassandra import Cassandra; c=Cassandra(settings(),False); print(c.cluster.metadata.export_schema_as_string()); c.close()"
    (directory / "schema.cql").write_text(run("docker", "exec", "threat-intelligence-airflow3-scheduler-1", "python", "-c", schema))
    snapshot = run("docker", "exec", PRIMARY, "nodetool", "snapshot", "-t", f"pre-cluster-{stamp}", "threat_intelligence", "system_auth")
    (directory / "snapshot.txt").write_text(snapshot)
    location = run("docker", "volume", "inspect", "--format", "{{.Mountpoint}}", VOLUME)
    try:
        run("docker", "stop", "--time", "120", PRIMARY)
        run("tar", "-czf", str(archive), "-C", location, ".", timeout=400)
    finally:
        run("docker", "start", PRIMARY)
    restore(directory, stamp, snapshot)


def restore(directory, stamp, snapshot):
    archive = directory / "cassandra.tar.gz"
    run("gzip", "--test", str(archive))
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()

    scratch = f"ti-cassandra-precluster-{stamp}"
    run("docker", "volume", "create", "--label", "ti.purpose=cassandra-migration-restore", scratch)
    scratch_path = run("docker", "volume", "inspect", "--format", "{{.Mountpoint}}", scratch)
    run("tar", "-xzf", str(archive), "-C", scratch_path)
    command = ["docker", "run", "-d", "--network", "none", "--name", scratch,
               "--hostname", "ti-restore", "--add-host", "ti-restore:127.0.0.1",
               "--memory", "2g", "-v", f"{scratch}:/var/lib/cassandra",
               "-v", f"{ROOT}/scripts/cassandra-secure-entrypoint.sh:/secure-entrypoint.sh:ro",
               "--entrypoint", "/bin/bash"]
    for name, value in {
        "CASSANDRA_CLUSTER_NAME": "ti-dev-single-node", "CASSANDRA_DC": "dc1", "CASSANDRA_RACK": "rack1",
        "CASSANDRA_ENDPOINT_SNITCH": "GossipingPropertyFileSnitch", "CASSANDRA_LISTEN_ADDRESS": "127.0.0.1",
        "CASSANDRA_RPC_ADDRESS": "127.0.0.1", "CASSANDRA_NUM_TOKENS": "16",
        "CASSANDRA_BROADCAST_ADDRESS": "127.0.0.1", "CASSANDRA_SEEDS": "127.0.0.1",
        "MAX_HEAP_SIZE": "768M", "HEAP_NEWSIZE": "128M",
    }.items():
        command += ["-e", f"{name}={value}"]
    run(*command, IMAGE, "/secure-entrypoint.sh", "cassandra", "-f")
    try:
        restored = json.loads(run("docker", "run", "--rm", "--network", f"container:{scratch}",
                                  "-v", f"{ROOT}/secrets/cassandra-writer-password:/run/secrets/password:ro",
                                  "--entrypoint", "python", "ti-app:local", "-c", CLIENT, "cassandra", timeout=300))
    finally:
        if run("docker", "inspect", "--format", "{{.State.Running}}", scratch) == "true":
            run("docker", "stop", "--time", "60", scratch)
    records, expected = restored["records"], restored["sha256_sum"]
    assert records == restored["unique"] and records >= 50000 and len(expected) == 64
    uploaded = [upload(p, f"backups/cassandra-migration-{stamp}/{p.name}") for p in sorted(directory.iterdir())]
    result = {"directory": str(directory), "snapshot": snapshot, "sha256": digest,
              "restored": restored, "objects": uploaded}
    (directory / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
