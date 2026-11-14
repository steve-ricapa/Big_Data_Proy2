"""Non-disruptive live health probes for services without native healthchecks.

Compose also declares native probes for the next authorized recreation.
This monitor does not restart or recreate application containers.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

PROBES = {
    "caddy": ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:2019/config/"],
    "keycloak": ["/bin/bash", "-c", "exec 3<>/dev/tcp/127.0.0.1/9000; printf 'GET /auth/health/ready HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n' >&3; grep -q 'HTTP/1.[01] 200' <&3"],
    "mcp-remote": ["python", "-c", "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=5)); assert r['status']=='ok' and r['auth']=='oidc'"],
    "airflow3-dag-processor": ["python", "-c", "import json,urllib.request; r=json.load(urllib.request.urlopen('http://airflow3-api:8080/api/v2/monitor/health',timeout=5)); assert r['dag_processor']['status']=='healthy'"],
}


def main():
    result = {"at": datetime.now(UTC).isoformat(), "mode": "external-monitor-no-recreation", "checks": {}}
    for service, command in PROBES.items():
        try:
            process = subprocess.run(["docker", "exec", f"threat-intelligence-{service}-1", *command], capture_output=True, timeout=20)
            status = "PASS" if process.returncode == 0 else "FAIL"
        except subprocess.TimeoutExpired:
            status = "FAIL"
        result["checks"][service] = status
    result["status"] = "PASS" if all(v == "PASS" for v in result["checks"].values()) else "FAIL"
    target = Path("/opt/threat-intelligence/docs/evidence/acceptance_v2/component_health.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    temporary.replace(target)
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
