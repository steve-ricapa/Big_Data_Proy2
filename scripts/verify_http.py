"""Run against the real local API; saves responses as evidence, never mocks."""

import json
from pathlib import Path

import httpx

base = "http://127.0.0.1:18000"
results = {}
with httpx.Client(timeout=30) as client:
    for path in (
        "/health",
        "/ready",
        "/api/v1/kpis",
        "/api/v1/analytics/cassandra/snapshot",
        "/api/v1/vulnerabilities?page_size=2",
        "/api/v1/cwes/top",
        "/api/v1/products/top",
        "/api/v1/pipeline/status",
    ):
        response = client.get(base + path)
        assert response.status_code == 200, (path, response.status_code)
        results[path] = response.json()
    identifier = results["/api/v1/vulnerabilities?page_size=2"]["items"][0]["cve_id"]
    for path in (
        "/api/v1/vulnerabilities/" + identifier,
        "/api/v1/graph/cve/" + identifier,
    ):
        response = client.get(base + path)
        assert response.status_code == 200, (path, response.status_code)
        results[path] = response.json()
    assert client.get(base + "/api/v1/vulnerabilities?page=0").status_code == 422
    assert client.get(base + "/api/v1/vulnerabilities?published_from=2026-02-30").status_code == 422
    assert (
        client.get(base + "/api/v1/vulnerabilities/CVE-2099-0000000").status_code == 404
    )
    assert client.get("http://127.0.0.1:18501/_stcore/health").status_code == 200
Path("docs/evidence/http_validation.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("14 HTTP checks passed against actual local API/dashboard services (including Cassandra).")
