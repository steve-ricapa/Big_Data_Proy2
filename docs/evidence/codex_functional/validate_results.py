"""Assert native authenticated tool outputs against the captured real NVD source."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from threat_intelligence.transformations.normalize import normalize  # noqa: E402

HERE = Path(__file__).resolve().parent
DIAG = HERE.parent / "codex_diagnosis"


def logged_json(path):
    return json.loads(next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("{")))


source_path = HERE / "nvd_CVE-2021-44228.json"
assert hashlib.sha256(source_path.read_bytes()).hexdigest() == "58671756e1d6de00aac65a9dd316cd912976e2695adebe21083a2558701d180f"
source = json.loads(source_path.read_text())
expected = normalize(source["vulnerabilities"][0])
native = json.loads((DIAG / "functional_native_after.json").read_text())
before = json.loads((DIAG / "functional_native_before.json").read_text())
calls = native["functional_calls"]
assert native["target"]["authStatus"] == "oAuth" and native["target"]["tool_count"] == 6
assert all(not item["isError"] for name, item in calls.items() if name != "missing_details")
assert {"keyword", "severity", "cve_id"} <= set(native["tool_input_fields"]["search_vulnerabilities"])
assert "cve_id" in native["tool_input_fields"]["get_affected_products"]
assert calls["details"]["result"] == expected
assert calls["products"]["result"]["items"] == expected["products"]
assert calls["products"]["result"]["cpes"] == expected["cpes"]
assert calls["search_exact"]["result"]["total"] == 1
assert calls["search_exact"]["result"]["items"][0]["cve_id"] == expected["cve_id"]
assert calls["combined"]["result"]["total"] == 1
assert calls["negative_combined"]["result"]["total"] == 0
assert calls["keyword_no_match"]["result"]["total"] == 0
assert calls["keyword"]["result"]["total"] == 10
assert all("log4j" in item["description"].lower() for item in calls["keyword"]["result"]["items"])
assert all(item["severity"] == "CRITICAL" for item in calls["severity"]["result"]["items"])
graph = calls["relationships"]["result"]
assert len(graph["items"]) == graph["limit"] == 250
assert graph["total_relationships"] == 559 and graph["truncated"] is True
assert any(item["relationship"] == "AFFECTS" and item["entity"]["id"] == '["a","apache","log4j"]' for item in graph["items"])
assert calls["missing_details"]["isError"] is True
assert "HTTP 404" in calls["missing_details"]["result"]["message"]
assert calls["known_existing_details"]["result"] == before["functional_calls"]["known_existing_details"]["result"]
stats = calls["stats"]["result"]
old_stats = before["functional_calls"]["stats"]["result"]
assert stats["total_cves"] == old_stats["total_cves"] + 1 == 174735
assert stats["severity"]["CRITICAL"] == old_stats["severity"]["CRITICAL"] + 1 == 17895
assert {k: v for k, v in stats["severity"].items() if k != "CRITICAL"} == {k: v for k, v in old_stats["severity"].items() if k != "CRITICAL"}
assert calls["legacy_products"]["result"]["items"] == stats["top_products"]
assert calls["cwes"]["result"]["items"] == stats["top_cwes"]
backend = logged_json(HERE / "backend_validation.log")
assert backend["status"] == "PASS" and all(v == "PASS" for v in backend["kpi_audit"]["checks"].values())
backfill = logged_json(HERE / "backfill_execution.log")
assert backfill["exit"] == 0 and backfill["records"][-1]["dag_active_restored"]
verify = next(item for item in backfill["records"] if item.get("stage") == "verify")
assert set(verify["counts"].values()) == {174735}
old_fingerprint = int("5d8d4de4bebf0d1cb4251cc7e7cc8c0e12fa255e13146ac5bd796e28581d02b1", 16)
increment = int(hashlib.sha256((expected["cve_id"] + ":" + expected["content_hash"]).encode()).hexdigest(), 16)
fingerprint = f"{(old_fingerprint + increment) % (1 << 256):064x}"
assert all(v["sha256_sum"] == fingerprint for v in verify["fingerprints"].values())
auth = {}
with httpx.Client(timeout=40) as client:
    for name, headers in (("no_authorization", {}), ("invalid_bearer", {"Authorization": "Bearer invalid-not-a-token"})):
        response = client.post("https://ti-136-114-21-18.sslip.io/mcp", headers={"Accept": "application/json, text/event-stream", **headers}, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "ti-functional-negative-check", "version": "1"}}})
        assert response.status_code == 401
        assert "resource_metadata=" in response.headers.get("www-authenticate", "")
        auth[name] = {"status": 401, "result": "PASS"}
result = {
    "at": datetime.now(UTC).isoformat(), "status": "PASS_TECHNICAL_FUNCTIONAL",
    "native_runtime_version": native["version"], "app_gui_retest": "PENDING_OWNER_CONFIRMATION",
    "tools": {name: "PASS" for name in ("search_vulnerabilities", "get_cve_details", "get_top_cwes", "get_vulnerability_statistics", "get_affected_products", "explore_cve_relationships")},
    "positive_native_calls": sum(not call["isError"] for call in calls.values()),
    "negative_missing_cve": "PASS_EXPECTED_HTTP404_TOOL_ERROR",
    "source_exact_match": True, "cvss": expected["cvss"], "product_count": len(expected["products"]),
    "cpe_count": len(expected["cpes"]), "graph_relationships": 559, "graph_response_limit": 250,
    "search_tests": {"exact_cve": "PASS", "keyword": "PASS", "severity": "PASS", "combined": "PASS", "no_match": "PASS"},
    "stats_before": old_stats["total_cves"], "stats_after": stats["total_cves"],
    "full_parity_fingerprint": fingerprint, "delta_matches_last_accepted_baseline_plus_one_source_cve": True,
    "independent_kpi_checks": backend["kpi_audit"]["checks"], "auth_rejection_checks": auth,
    "dag_active_restored": True, "oauth_configuration_changed": False,
}
(HERE / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
