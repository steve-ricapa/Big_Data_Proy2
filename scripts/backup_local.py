"""Coordinated cold backups of this project's named volumes only.

Stops writers before databases; restores exactly the previously running services.
Archives contain database content/auth stores: private backup directory, not Git.
"""

import hashlib
import json
import os
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.airflow3.yml"]
if (ROOT / "secrets/cassandra-admin-password").exists():
    COMPOSE += ["-f", "docker-compose.secure.yml"]
WRITERS = ["airflow3-scheduler", "airflow3-dag-processor", "airflow3-api", "api", "dashboard"]
DATABASES = ["mongodb", "cassandra", "neo4j", "airflow3-postgres"]
VOLUMES = ["mongodb_data", "cassandra_data", "neo4j_data", "airflow3_postgres", "checkpoint_data", "airflow3_auth"]
if (ROOT / "secrets/public.env").exists():
    COMPOSE += ["--env-file", str(ROOT / "secrets/public.env"), "-f", "docker-compose.public.yml"]
    WRITERS += ["mcp-remote", "caddy", "keycloak"]
    DATABASES += ["keycloak-db"]
    VOLUMES += ["keycloak_postgres", "caddy_data", "caddy_config"]


def run(args):
    return subprocess.run(args, cwd=ROOT, env=dict(os.environ), check=True, capture_output=True, text=True).stdout


def main():
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    directory = Path(os.getenv("TI_BACKUP_DIR", str(ROOT / "backups"))) / stamp
    directory.mkdir(parents=True, exist_ok=False)
    directory.chmod(0o700)
    running = run([*COMPOSE, "ps", "--services", "--status", "running"]).splitlines()
    # Refuse to snapshot an active ETL: stopping a task mid-commit is not a backup protocol.
    probe = "from airflow.models import DagRun; from airflow.utils.session import create_session;\nwith create_session() as s: assert s.query(DagRun).filter(DagRun.state.in_(['queued','running'])).count()==0, 'Active DAG: pause and wait before backup'"
    run([*COMPOSE, "exec", "-T", "airflow3-scheduler", "python", "-c", probe])
    result = {"started_at": datetime.now(UTC).isoformat(), "type": "coordinated-cold-volumes", "directory": str(directory), "archives": [], "status": "IN_PROGRESS"}
    try:
        for group in (WRITERS, DATABASES):
            selected = [name for name in group if name in running]
            if selected:
                run([*COMPOSE, "stop", "--timeout", "120", *selected])
        for name in VOLUMES:
            volume = "threat-intelligence_" + name
            run(["docker", "volume", "inspect", volume])
            code = "import tarfile;\nwith tarfile.open('/backup/" + name + ".tar.gz','w:gz',compresslevel=1) as t: t.add('/source',arcname='data')"
            run(["docker", "run", "--rm", "--user", "0:0", "--network", "none", "--mount", f"type=volume,source={volume},target=/source,readonly", "--mount", f"type=bind,source={directory},target=/backup", "--entrypoint", "python", "ti-app:local", "-c", code])
            path = directory / (name + ".tar.gz")
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            # Read the entire gzip/tar stream, checking CRC/truncation, not just header.
            count = 0
            with tarfile.open(path, "r|gz") as archive:
                for member in archive:
                    if member.isfile():
                        stream = archive.extractfile(member)
                        while stream.read(1024 * 1024):
                            pass
                    count += 1
            result["archives"].append({"volume": volume, "file": path.name, "bytes": path.stat().st_size, "sha256": digest, "members": count})
            (directory / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        config = directory / "configuration.tar.gz"
        with tarfile.open(config, "w:gz") as archive:
            for relative in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml", "scripts", "src", "airflow/dags", "infrastructure", "pyproject.toml", "uv.lock"):
                path = ROOT / relative
                archive.add(path, arcname=relative, filter=lambda member: None if any(part in (".terraform", "__pycache__") for part in Path(member.name).parts) or ".tfstate" in member.name or member.name.endswith((".tfplan", ".tfvars")) else member)
        result["status"] = "SUCCESS"
    finally:
        for group in (DATABASES, WRITERS):
            selected = [name for name in group if name in running]
            if selected:
                run([*COMPOSE, "up", "-d", "--wait", *selected, "--wait-timeout", "360"])
        result["finished_at"] = datetime.now(UTC).isoformat()
        (directory / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (ROOT / "docs/evidence/backup_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
