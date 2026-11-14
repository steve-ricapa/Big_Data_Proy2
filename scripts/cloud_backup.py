"""Coordinated private cloud backup + resumable GCS upload using VM identity."""

import hashlib
import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path("/opt/threat-intelligence")
COMPOSE = ["docker", "compose", "--env-file", "secrets/public.env"]
for name in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml"):
    COMPOSE += ["-f", name]


def upload(path, key):
    request = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token", headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(request, timeout=15) as response:
        token = json.load(response)["access_token"]
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    url = "https://storage.googleapis.com/upload/storage/v1/b/proyectobigdata2-514216-ti-dev-processed/o?uploadType=resumable"
    request = urllib.request.Request(url, method="POST", data=json.dumps({"name": key, "metadata": {"sha256": digest}}).encode(), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "X-Upload-Content-Length": str(path.stat().st_size)})
    with urllib.request.urlopen(request, timeout=30) as response:
        location = response.headers["Location"]
    assert urllib.parse.urlparse(location).hostname == "storage.googleapis.com"
    with path.open("rb") as stream:
        body = iter(lambda: stream.read(8 * 1024 * 1024), b"")
        request = urllib.request.Request(location, method="PUT", data=body, headers={"Authorization": "Bearer " + token, "Content-Type": "application/octet-stream", "Content-Length": str(path.stat().st_size)})
        with urllib.request.urlopen(request, timeout=300) as response:
            assert json.load(response)["name"] == key
    return {"object": key, "bytes": path.stat().st_size, "sha256": digest, "uploaded": True}


def main():
    os.chdir(ROOT)
    probe = "from airflow.models import DagModel;from airflow.utils.session import create_session;\nwith create_session() as s: print('PAUSED' if s.query(DagModel).filter_by(dag_id='nvd_threat_intelligence').one().is_paused else 'ACTIVE')"
    previous = subprocess.run([*COMPOSE, "exec", "-T", "airflow3-scheduler", "python", "-c", probe], check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]
    subprocess.run([*COMPOSE, "exec", "-T", "airflow3-scheduler", "airflow", "dags", "pause", "nvd_threat_intelligence"], check=True, capture_output=True)
    try:
        environment = dict(os.environ, TI_BACKUP_DIR="/srv/ti-data/backups")
        subprocess.run(["python3", "scripts/backup_local.py"], check=True, env=environment)
        backup = json.loads(Path("docs/evidence/backup_validation.json").read_text())
        assert backup["status"] == "SUCCESS"
        directory = Path(backup["directory"])
        uploaded = [upload(path, f"backups/{directory.name}/{path.name}") for path in sorted(directory.iterdir()) if path.is_file()]
        result = {"status": "SUCCESS", "directory": str(directory), "objects": uploaded, "retention": "GCS lifecycle7d + soft-delete7d; local preserved", "dag_originally_paused": previous == "PAUSED"}
        Path("docs/evidence/cloud_backup_upload.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    finally:
        if previous == "ACTIVE":
            subprocess.run([*COMPOSE, "exec", "-T", "airflow3-scheduler", "airflow", "dags", "unpause", "nvd_threat_intelligence"], check=True, capture_output=True)


if __name__ == "__main__":
    main()
