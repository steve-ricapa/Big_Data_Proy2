"""Validate deployment inputs and build verification tags without deployment."""

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/opt/threat-intelligence")
OUT = ROOT / "docs/evidence/acceptance_v2"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert (ROOT / ".dockerignore").exists(), "Build context must exclude secrets/data before any build"
    compose = ["docker", "compose", "--env-file", "secrets/public.env"]
    for path in ("docker-compose.yml", "docker-compose.airflow3.yml", "docker-compose.secure.yml", "docker-compose.public.yml"):
        compose += ["-f", path]
    subprocess.run([*compose, "config", "--quiet"], cwd=ROOT, check=True)
    result = {"at": datetime.now(UTC).isoformat(), "compose_config": "PASS", "images": {}, "existing_tags_replaced": False, "infrastructure_recreated": False}
    before = subprocess.run(["docker", "ps", "--no-trunc", "--format", "{{.ID}}", "--filter", "label=com.docker.compose.project=threat-intelligence"], check=True, capture_output=True, text=True).stdout.split()
    result["production_container_ids_before"] = sorted(before)
    for label, dockerfile, target in (("app", "infrastructure/docker/python.Dockerfile", "runtime"), ("test", "infrastructure/docker/python.Dockerfile", "test"), ("mcp", "infrastructure/docker/python.Dockerfile", "mcp"), ("airflow", "infrastructure/docker/airflow3.Dockerfile", None)):
        tag = f"ti-v2-{label}:verification"
        args = ["docker", "build", "--pull=false", "-f", dockerfile, "-t", tag]
        if target:
            args += ["--target", target]
        args.append(".")
        with (OUT / f"build_{label}.log").open("w") as log:
            process = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1200, env=dict(os.environ, DOCKER_BUILDKIT="1"))
        result["images"][label] = {"status": "PASS" if process.returncode == 0 else "FAIL", "tag": tag}
        if process.returncode == 0:
            result["images"][label]["image_id"] = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], check=True, capture_output=True, text=True).stdout.strip()
        (OUT / "rebuild.json").write_text(json.dumps(result, indent=2))
    result["inputs_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ("pyproject.toml", "requirements.lock", "requirements-mcp.lock", "airflow/requirements.lock", "infrastructure/docker/python.Dockerfile", "infrastructure/docker/airflow3.Dockerfile", ".dockerignore")}
    after = subprocess.run(["docker", "ps", "--no-trunc", "--format", "{{.ID}}", "--filter", "label=com.docker.compose.project=threat-intelligence"], check=True, capture_output=True, text=True).stdout.split()
    result["production_container_ids_unchanged"] = sorted(before) == sorted(after)
    result["status"] = "PASS" if all(i["status"] == "PASS" for i in result["images"].values()) and result["production_container_ids_unchanged"] else "PARTIAL"
    result["limits"] = ["Uses existing base-image/build caches; no clean-host rebuild", "Base images are version-tagged, not digest-pinned", "No Terraform apply, VM recreation, database migration, production image replacement or registry push"]
    (OUT / "rebuild.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
