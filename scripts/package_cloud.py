"""Allowlisted cloud source bundle. No secrets, datasets, state or local volumes."""

import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
destination = Path.home() / "AppData/Local/Temp/opencode/ti-cloud-source.tar.gz"
sources = [root / name for name in (".dockerignore", "src", "services", "scripts", "airflow/dags", "airflow/tests", "airflow/requirements.in", "airflow/requirements.lock", "infrastructure/docker", "infrastructure/scripts", "tests", "README.md", "pyproject.toml", "requirements.lock", "requirements-mcp.lock", "uv.lock", "docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml")]
with tarfile.open(destination, "w:gz") as archive:
    for source in sources:
        archive.add(source, arcname=source.relative_to(root).as_posix(), filter=lambda member: None if "__pycache__" in Path(member.name).parts else member)
with destination.open("rb") as stream:
    digest = hashlib.file_digest(stream, "sha256").hexdigest()
result = {"bundle": str(destination), "bytes": destination.stat().st_size, "sha256": digest, "excluded": ["secrets", "data", "terraform state/plans", "backups", "local volumes", "credentials"]}
(root / "docs/evidence/gcp_source_bundle.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
