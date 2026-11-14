"""External HTTPS API/Streamlit checks; no credentials in output or artifacts."""

import json
import socket
import ssl
import time
from datetime import UTC, datetime
from pathlib import Path

import certifi
import httpx
from cloud_test_credentials import load

HOST = "ti-136-114-21-18.sslip.io"
base = "https://" + HOST
credentials = load()
result = {"at": datetime.now(UTC).isoformat(), "base_url": base, "checks": {}}
with socket.create_connection((HOST, 443), timeout=15) as stream, ssl.create_default_context(cafile=certifi.where()).wrap_socket(stream, server_hostname=HOST) as secure:
    cert = secure.getpeercert()
    result["tls"] = {"verified": True, "protocol": secure.version(), "expires": cert["notAfter"]}
with httpx.Client(timeout=45) as client:
    for path in ("/", "/api/v1/kpis", "/docs"):
        response = client.get(base + path)
        assert response.status_code == 401, path
        result["checks"]["unauth:" + path] = "PASS"
    response = client.post(base + "/mcp", headers={"Accept": "application/json, text/event-stream"}, json={"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}})
    assert response.status_code == 401
    result["checks"]["unauth:mcp"] = "PASS"
    for path in ("/auth/admin/", "/auth/realms/master/"):
        assert client.get(base + path).status_code == 404
        result["checks"]["private_admin:" + path] = "PASS"
    for path in ("/.well-known/oauth-protected-resource/mcp", "/auth/realms/ti/.well-known/openid-configuration"):
        response = client.get(base + path)
        assert response.status_code == 200, (path, response.status_code)
        result["checks"][path] = "PASS"
    client.auth = httpx.BasicAuth("ti-demo", credentials["web-password"])
    for path in ("/", "/_stcore/health", "/health", "/ready", "/api/v1/kpis", "/api/v1/vulnerabilities?page_size=2", "/api/v1/cwes/top", "/api/v1/products/top", "/api/v1/analytics/cassandra/snapshot", "/api/v1/pipeline/status", "/docs"):
        start = time.monotonic()
        response = client.get(base + path)
        assert response.status_code == 200, (path, response.status_code)
        result["checks"]["authenticated:" + path] = {"status": "PASS", "seconds": round(time.monotonic() - start, 3)}
        if path == "/api/v1/kpis":
            result["total_cves"] = response.json()["total_cves"]
        if path == "/api/v1/vulnerabilities?page_size=2":
            identifier = response.json()["items"][0]["cve_id"]
    for path in ("/api/v1/vulnerabilities/" + identifier, "/api/v1/graph/cve/" + identifier):
        assert client.get(base + path).status_code == 200
        result["checks"][path] = "PASS"
Path("docs/evidence/gcp_https_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
