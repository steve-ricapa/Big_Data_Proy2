"""Read-only ADC checks. Never prints tokens or reads credential files directly."""

import json
from datetime import UTC, datetime
from pathlib import Path

import google.auth
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession, Request
from requests.exceptions import RequestException

PROJECT = "proyectobigdata2-514216"
credentials, detected_project = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
result = {
    "checked_at": datetime.now(UTC).isoformat(),
    "project_id": PROJECT,
    "credential_type": type(credentials).__name__,
    "detected_project": detected_project,
    "read_only": True,
}
try:
    credentials.refresh(Request())
    result["adc_refresh"] = "PASS"
except (GoogleAuthError, RequestException) as error:
    # Exception bodies can contain credential metadata; do not log them.
    result["adc_refresh"] = "FAIL"
    result["error_type"] = type(error).__name__

if result["adc_refresh"] == "PASS":
    with AuthorizedSession(credentials) as session:
        for name, url, params in (
            ("project_read", f"https://cloudresourcemanager.googleapis.com/v3/projects/{PROJECT}", {}),
            ("enabled_services", f"https://serviceusage.googleapis.com/v1/projects/{PROJECT}/services", {"filter": "state:ENABLED", "pageSize": 200}),
        ):
            response = session.get(url, params=params, timeout=45)
            data = response.json()
            check = {"http_status": response.status_code}
            if response.ok:
                if name == "enabled_services":
                    check["services"] = sorted(s["config"]["name"] for s in data.get("services", []))
                    check["has_more_pages"] = bool(data.get("nextPageToken"))
                else:
                    check["project_id"] = data.get("projectId")
                    check["state"] = data.get("state")
            else:
                check["reasons"] = [d["reason"] for d in data.get("error", {}).get("details", []) if "reason" in d]
            result[name] = check

path = Path("docs/evidence/gcp_connection_check.json")
path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
