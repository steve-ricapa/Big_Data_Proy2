"""Initialize project Secret Manager versions without plaintext in LLM/log/state.

Reads cloud-generated app secrets through private IAP into process memory only.
Uses existing impersonated ADC; skips already initialized secrets, no rotations.
"""

import base64
import json
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

code = "import json;from pathlib import Path;p=Path('/opt/threat-intelligence/secrets');print(json.dumps({f.name:f.read_text() for f in p.iterdir() if f.is_file()}))"
result = subprocess.run([sys.executable, "scripts/gcp_remote.py", "--command", "sudo python3 -c " + shlex.quote(code)], check=False, capture_output=True, text=True, encoding="utf-8")
if result.returncode:
    raise RuntimeError("Private IAP secret transfer failed; response suppressed")
values = json.loads(result.stdout)
mapping = {
    "mongodb-uri": "mongodb-writer-uri",
    "mongodb-root-password": "mongodb-root-password",
    "cassandra-password": "cassandra-writer-password",
    "neo4j-password": "neo4j-password",
    "postgres-password": "postgres-password",
    "airflow-db-uri": "airflow3-db-uri",
    "airflow-fernet-key": "airflow-fernet-key",
    "airflow-web-key": "airflow3-jwt",
}
payloads = {name: values[file].encode() for name, file in mapping.items()}
payloads["runtime-bootstrap"] = json.dumps(values).encode()
credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
evidence = {"at": datetime.now(UTC).isoformat(), "project": "proyectobigdata2-514216", "secrets": [], "plaintext_logged": False, "terraform_secret_values": False}
with AuthorizedSession(credentials) as session:
    for name, payload in payloads.items():
        base = "https://secretmanager.googleapis.com/v1/projects/proyectobigdata2-514216/secrets/ti-dev-" + name
        response = session.get(base + "/versions", params={"filter": "state:ENABLED"}, timeout=30)
        response.raise_for_status()
        if response.json().get("versions"):
            evidence["secrets"].append({"id": "ti-dev-" + name, "status": "existing_enabled_version_preserved"})
            continue
        response = session.post(base + ":addVersion", json={"payload": {"data": base64.b64encode(payload).decode()}}, timeout=30)
        if not response.ok:
            raise RuntimeError("Secret version creation failed with HTTP " + str(response.status_code))
        evidence["secrets"].append({"id": "ti-dev-" + name, "status": "version_created", "version": response.json()["name"].split("/")[-1]})
Path("docs/evidence/gcp_secret_versions.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
print(json.dumps(evidence))
