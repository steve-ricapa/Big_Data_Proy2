"""Resume initial cloud load from preserved per-engine checkpoints, sequentially."""

import os
import subprocess
from pathlib import Path

os.chdir("/opt/threat-intelligence")
if Path("secrets/cassandra-cluster.env").exists():
    raise SystemExit("Legacy initial load is not supported on the distributed deployment; use the incremental DAG")
compose = ["docker", "compose", "--env-file", "secrets/public.env"]
for name in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml"):
    compose += ["-f", name]
for stage in ("mongodb", "cassandra", "neo4j", "kpis", "verify"):
    subprocess.run([*compose, "run", "--rm", "--no-deps", "runner", stage, "--run-dir", "data/staging/cloud_initial"], check=True)
print("Cloud initial load complete and verified; inspect structured stage results.", flush=True)
