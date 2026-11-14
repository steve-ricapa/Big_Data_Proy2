"""Publish durable app images to the private Artifact Registry from the VM.

Authenticates with the VM service account token, never persists it: docker
credentials live in a temporary DOCKER_CONFIG directory removed afterwards.
"""

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/opt/threat-intelligence")
HOST = "us-central1-docker.pkg.dev"
REPO = "us-central1-docker.pkg.dev/proyectobigdata2-514216/ti-dev-images"
IMAGES = {"ti-app:local": "ti-app", "ti-airflow:3.4-local": "ti-airflow", "ti-mcp:local": "ti-mcp"}
TAG = datetime.now(UTC).strftime("%Y%m%d")


def token():
    request = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)["access_token"]


def main():
    os.chdir(ROOT)
    access = token()
    config = tempfile.mkdtemp(prefix="docker-push-")
    os.chmod(config, 0o700)
    environment = dict(os.environ, DOCKER_CONFIG=config)
    result = {"at": datetime.now(UTC).isoformat(), "repository": REPO, "tag": TAG, "images": [], "status": "IN_PROGRESS"}
    try:
        subprocess.run(["docker", "login", REPO, "--username", "oauth2accesstoken", "--password-stdin"], input=access, text=True, check=True, capture_output=True, env=environment)
        for source, name in IMAGES.items():
            digests = set()
            for tag in (TAG, "latest"):
                subprocess.run(["docker", "tag", source, f"{REPO}/{name}:{tag}"], check=True, env=environment)
                push = subprocess.run(["docker", "push", f"{REPO}/{name}:{tag}"], check=True, capture_output=True, text=True, env=environment).stdout
                digests.update(line.split("digest: sha256:", 1)[1].split()[0] for line in push.splitlines() if "digest: sha256:" in line)
            result["images"].append({"source": source, "remote": f"{REPO}/{name}", "tags": [TAG, "latest"], "digests": sorted(digests)})
        subprocess.run(["docker", "logout", REPO], check=True, capture_output=True, env=environment)
        # Independent verification: the registry API lists the pushed tags.
        catalog = {}
        for name in IMAGES.values():
            request = urllib.request.Request(f"https://{HOST}/v2/{REPO.split('/', 1)[1]}/{name}/tags/list", headers={"Authorization": "Bearer " + access})
            with urllib.request.urlopen(request, timeout=30) as response:
                catalog[name] = sorted(json.load(response).get("tags", []))
        result["catalog_check"] = catalog
        for name, tags in catalog.items():
            assert TAG in tags and "latest" in tags, f"Registry catalog missing tags for {name}: {tags}"
        result["status"] = "SUCCESS"
    finally:
        shutil.rmtree(config, ignore_errors=True)
    (ROOT / "docs/evidence/gcp_image_publish.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
