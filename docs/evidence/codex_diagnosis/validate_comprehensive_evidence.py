"""Reconcile saved evidence; never promotes SDK integration into OAuth E2E."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read_json(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def logged_json(name):
    return json.loads(next(line for line in (HERE / name).read_text(encoding="utf-8").splitlines() if line.startswith("{")))


candidate = read_json("comprehensive_canary.json")
production = read_json("comprehensive_production.json")
assert candidate["status"] == production["status"] == "PASS_INTEGRATION_NOT_OAUTH_E2E"
assert len(candidate["cases"]) == 59 and candidate["calls"] == 286
assert len(production["cases"]) == 63 and production["calls"] == 291
assert all(case["status"] == "PASS" for case in production["cases"])
assert len(production["schemas"]) == 6
assert all(tool["inputSchema"]["additionalProperties"] is False and tool["outputSchema"]["properties"] for tool in production["schemas"].values())
before = read_json("comprehensive_database.json")
after = read_json("comprehensive_database_after.json")
for key in ("mongodb", "cassandra", "neo4j", "snapshot", "independent_catalog"):
    assert before[key] == after[key]
assert after["mongodb"] == after["cassandra"] == after["neo4j"]
assert after["mongodb"]["records"] == 174735 and after["mongodb"]["duplicate_ids"] == 0
reference = after["independent_catalog"]
assert production["catalog_reference"]["total"] == reference["total"] == 23186
assert production["catalog_reference"]["id_count_sha256"] == reference["id_count_sha256"]
activation = logged_json("comprehensive_activation.log")
assert activation["changed_containers"] == ["api", "mcp-remote"]
assert activation["other_container_ids_unchanged"] and activation["oauth_verifier_and_security_ast_unchanged"]
for name, digest in activation["source_hashes"].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
assert "90 passed, 8 skipped" in (HERE / "comprehensive_local_tests.log").read_text(encoding="utf-8")
assert "All checks passed" in (HERE / "comprehensive_ruff.log").read_text(encoding="utf-8")
native = read_json("comprehensive_native_suite.json")
assert native["status"] == "PENDING_USER_LOGIN" and native["authStatus"] == "notLoggedIn"
auth = read_json("comprehensive_external_auth.json")
assert auth["no_bearer"] == auth["invalid_bearer"] == 401
health = logged_json("comprehensive_final_health.log")
assert health["scheduler"]["dag_active"] and health["scheduler"]["active_runs"] == 0
assert not health["backup_active"]
assert all(not item["unexpected_error_labels"] for item in health["services"].values())
report = ROOT / "docs/integrations/mcp_comprehensive_remediation.md"
text = report.read_text(encoding="utf-8")
assert sum(line.startswith("```") for line in text.splitlines()) % 2 == 0
assert all(target.startswith(("https://", "http://", "#")) or (report.parent / target).exists() for target in re.findall(r"\]\(([^)]+)\)", text))
artifacts = [report, *HERE.glob("comprehensive*.json"), *HERE.glob("comprehensive*.log")]
assert not any(re.search(r"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", path.read_text(encoding="utf-8")) for path in artifacts)
summary = {
    "at": datetime.now(UTC).isoformat(), "status": "APPLIED_ACCEPTANCE_PENDING",
    "reported_audit": {"inventoried": 100, "executed": 96, "pass": 77, "fail": 4, "warning": 15, "not_tested_additional": 4},
    "original_96_replay": "Only supplied scenarios reproduced; no fabricated one-to-one replay",
    "local_tests": {"pass": 90, "skipped": 8, "fail": 0},
    "candidate": {"checks_pass": 59, "sdk_calls": 286},
    "production": {"checks_pass": 63, "sdk_calls": 291, "transport": "SDK -> real HTTP API -> databases, not authenticated public MCP E2E"},
    "three_engine_consistency": after["mongodb"],
    "catalog": reference,
    "original_not_tested": {"N01": "Original/final SDK schemas inspected; native reception pending login", "N02": "PASS_559_UNIQUE_EDGES", "N03": "PASS_THREE_ENGINES", "N04": "PASS_23186_PRODUCTS_RECONCILED"},
    "native_oauth": "PENDING_USER_LOGIN", "app_gui": "PENDING_OWNER_CONFIRMATION",
    "payload_defaults": "LEGACY_PRESERVED_SUMMARY_DEFAULT_REQUIRES_APPROVAL",
    "backfill": "DESIGN_ONLY_NOT_EXECUTED", "historical_data_rewritten": False,
    "credentials_changed": False, "keycloak_changed": False,
    "changed_containers": activation["changed_containers"], "other_container_ids_unchanged": True,
    "oauth_security_ast_unchanged": True, "dag_active": True,
    "modified_files_ruff": "PASS", "jwt_pattern_scan": "PASS",
    "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
}
(HERE / "comprehensive_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
