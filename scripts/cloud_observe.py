"""Bounded VM health telemetry using runtime identity; never logs tokens/secrets."""

import json
import os
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError


def metadata(path):
    request = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/" + path, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode()


def post(url, payload, token):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status


def main():
    project = "proyectobigdata2-514216"
    instance = metadata("instance/id")
    zone = metadata("instance/zone").split("/")[-1]
    token = json.loads(metadata("instance/service-accounts/default/token"))["access_token"]
    # Define the age metric even before the first successful sync. Do not emit
    # a fake zero/fresh checkpoint just to make an alert filter deployable.
    try:
        post(f"https://monitoring.googleapis.com/v3/projects/{project}/metricDescriptors", {"type": "custom.googleapis.com/threat_intelligence/nvd_sync_age_hours", "metricKind": "GAUGE", "valueType": "DOUBLE", "unit": "h", "description": "Hours since a successful verified NVD synchronization; absent until first success"}, token)
    except HTTPError as error:
        if error.code != 409:
            raise
    memory = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith(("MemTotal:", "MemAvailable:"))}
    disk = os.statvfs("/srv/ti-data")
    ids = subprocess.run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=threat-intelligence"], check=True, capture_output=True, text=True).stdout.split()
    containers = json.loads(subprocess.run(["docker", "inspect", *ids], check=True, capture_output=True, text=True).stdout) if ids else []
    # Do not include configuration/env from inspect output in telemetry.
    services = {"mongodb", "cassandra", "neo4j", "api", "dashboard", "airflow3-postgres", "airflow3-api", "airflow3-scheduler", "airflow3-dag-processor", "keycloak-db", "keycloak", "mcp-remote", "caddy"}
    # Scratch clients can inherit image labels; only canonical service instances
    # belong to the production health metric.
    required = [c for c in containers if c["Name"] in {f"/threat-intelligence-{name}-1" for name in services}]
    unhealthy = [c["Name"].lstrip("/") for c in required if not c["State"]["Running"] or c["State"].get("Health", {}).get("Status") == "unhealthy"]
    present = {c["Config"]["Labels"].get("com.docker.compose.service") for c in required}
    unhealthy += ["missing:" + name for name in sorted(services - present)]
    probe_path = Path("/opt/threat-intelligence/docs/evidence/acceptance_v2/component_health.json")
    try:
        probes = json.loads(probe_path.read_text())
        age = time.time() - datetime.fromisoformat(probes["at"]).timestamp()
        fresh = 0 <= age < 180
        for name in ("caddy", "keycloak", "mcp-remote", "airflow3-dag-processor"):
            if not fresh or probes.get("checks", {}).get(name) != "PASS":
                unhealthy.append(f"threat-intelligence-{name}-1")
    except (OSError, ValueError, KeyError):
        unhealthy.append("component-health-monitor:unavailable")
    unhealthy = sorted(set(unhealthy))
    values = {"memory_used_percent": 100 * (1 - memory["MemAvailable"] / memory["MemTotal"]), "disk_used_percent": 100 * (1 - disk.f_bavail / disk.f_blocks), "unhealthy_containers": len(unhealthy)}
    sync = Path("/srv/ti-data/docker/volumes/threat-intelligence_checkpoint_data/_data/nvd_sync.json")
    if sync.exists():
        checkpoint = json.loads(sync.read_text())
        values["nvd_sync_age_hours"] = (time.time() - datetime.fromisoformat(checkpoint["committed_at"]).timestamp()) / 3600
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    series = [{"metric": {"type": "custom.googleapis.com/threat_intelligence/" + name}, "resource": {"type": "gce_instance", "labels": {"project_id": project, "instance_id": instance, "zone": zone}}, "points": [{"interval": {"endTime": now}, "value": {"doubleValue": float(value)}}]} for name, value in values.items()]
    post(f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries", {"timeSeries": series}, token)
    log = {"logName": f"projects/{project}/logs/ti-dev-health", "resource": {"type": "gce_instance", "labels": {"project_id": project, "instance_id": instance, "zone": zone}}, "entries": [{"severity": "ERROR" if unhealthy else "INFO", "jsonPayload": {"at": now, "metrics": values, "unhealthy": unhealthy}}]}
    post("https://logging.googleapis.com/v2/entries:write", log, token)
    print(json.dumps({"at": now, "metrics": values, "unhealthy": unhealthy, "monitoring_write": "PASS", "logging_write": "PASS"}))


if __name__ == "__main__":
    main()
