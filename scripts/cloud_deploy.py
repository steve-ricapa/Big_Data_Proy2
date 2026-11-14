"""Build and start the approved single-VM cloud stack; no fake readiness claims."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--hostname", required=True)
parser.add_argument("--secure-compose-source")
args = parser.parse_args()
root = Path("/opt/threat-intelligence")
if args.secure_compose_source:
    shutil.copyfile(Path(args.secure_compose_source).resolve(), root / "docker-compose.secure.yml")
os.chdir(root)
assert os.path.ismount("/srv/ti-data"), "Data disk must be mounted before starting Docker workloads"
subprocess.run(["python3", "scripts/prepare_public_services.py", "--hostname", args.hostname], check=True)
for path in Path("secrets").iterdir():
    path.chmod(0o444)
    os.chown(path, 0, 0)
Path("secrets").chmod(0o700)
compose = ["docker", "compose", "--env-file", "secrets/public.env", "-f", "docker-compose.yml", "-f", "docker-compose.airflow3.yml", "-f", "docker-compose.secure.yml", "-f", "docker-compose.public.yml"]
subprocess.run([*compose, "build", "runner", "tester", "mcp", "airflow3-init"], check=True)
subprocess.run(["docker", "pull", "caddy:2.10.2-alpine"], check=True)
password = Path("secrets/web-password").read_text().strip()
hashing = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "caddy:2.10.2-alpine", "caddy", "hash-password"], input=password + "\n", capture_output=True, text=True, check=True)
hashed = hashing.stdout.strip()
assert hashed.startswith("$2"), "Unexpected password hash output"
hash_path = Path("secrets/web-password-hash")
hash_path.write_text(hashed, encoding="utf-8")
hash_path.chmod(0o444)
subprocess.run([*compose, "up", "-d", "--wait", "mongodb", "cassandra", "neo4j", "airflow3-postgres", "--wait-timeout", "420"], check=True)
for service in ("mongo-init", "cassandra-init", "airflow3-init"):
    subprocess.run([*compose, "run", "--rm", "--no-deps", service], check=True)
subprocess.run([*compose, "up", "-d", "--wait", "api", "dashboard", "airflow3-api", "airflow3-scheduler", "airflow3-dag-processor", "--wait-timeout", "300"], check=True)
# Source integrity before initial cloud loading; archive copies must match originals.
expected = {
    2024: "777bc4d2eea97ef6bbb0a0597b505c10a6c40968388678a7d22b9f45b70a6682",
    2025: "17485621d19368646fd12c7681517e96bd1606f001ffe74b4b0567e3f54ba78d",
    2026: "bbffab4cfabfe5f69adadf5ad056382c89f5953206d57dd504a6ac57d8dba687",
}
for year, digest in expected.items():
    path = Path(f"data/raw/nvd/{year}/nvdcve-2.0-{year}.json")
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
    print(json.dumps({"stage": "cloud_raw_integrity", "year": year, "sha256": digest, "result": "PASS"}), flush=True)
print("Cloud databases/web/Airflow started; raw hashes verified. Initial loading is a separate explicit step.", flush=True)
