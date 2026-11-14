"""Validate closure artifacts and produce a machine-readable evidence index."""

import hashlib
import json
import re
import tarfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/evidence/acceptance_v2"


def read(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def main():
    state = read("final_state.json")
    counts = state["databases"]
    assert len({(r["unique"], r["sha256_sum"]) for r in counts.values()}) == 1
    assert all(r["duplicate_ids"] == 0 for r in counts.values())
    assert state["airflow"]["paused"] is False and not state["airflow"]["active_runs"]
    assert all(t["state"] == "success" for t in state["airflow"]["tasks"]) and len(state["airflow"]["tasks"]) == 7
    restore = read("restore_three.json")
    assert restore["source"] == "private-gcs-download" and restore["status"] == "PASS"
    assert all(v["status"] == "PASS" for v in restore["engines"].values())
    assert read("crud.json")["cleanup_verified"] is True
    assert all(value == "PASS" for ops in read("crud.json")["engines"].values() for value in ops.values())
    assert read("component_health.json")["status"] == "PASS"
    assert read("rebuild.json")["status"] == "PASS"
    assert read("input_validation.json")["status"] == "PASS"
    assert all(read("quality.json")["kpi"]["independent_checks"].values())
    assert read("http.json")["total_cves"] == counts["mongodb"]["records"]
    assert all(value == "PASS" for value in read("mcp.json")["checks"].values())
    browser = read("browser.json")
    assert len(browser["views"]) == 5 and browser["graph_dom"][0]["svg"] >= 1
    assert all((ROOT / view["file"]).stat().st_size == view["bytes"] for view in browser["views"])
    local = re.search(r"(\d+) passed, (\d+) skipped", (BASE / "local_tests.log").read_text())
    assert local and tuple(map(int, local.groups())) == (47, 8)
    cases = ET.parse(BASE / "cloud_tests.xml").findall(".//testcase")
    assert len(cases) == 55 and all(c.find("failure") is None and c.find("error") is None and c.find("skipped") is None for c in cases)
    bundle = read("source_bundle.json")
    with tarfile.open(bundle["bundle"]) as archive:
        names = archive.getnames()
    assert ".dockerignore" in names
    assert not any(set(Path(name).parts) & {"secrets", "data", "backups", ".terraform"} for name in names)
    result = {
        "at": datetime.now(UTC).isoformat(),
        "counts": counts,
        "cloud_tests": {"passed": len(cases), "failed": 0, "skipped": 0, "image": "ti-v2-test:verification"},
        "local_tests": {"passed": 47, "skipped": 8, "scope": "Windows, integration disabled"},
        "academic": {"verified": 17, "total": 17, "percent": 100, "scope": "Original functional/documentary criteria; controlled Docker builds, not fresh-VM/bitwise reproduction"},
        "cloud_checklist": {"verified": 13, "total": 15, "percent": 86.7, "partial": ["Docker native healthchecks 9/13; 4 external probes active", "Billing budget visibility denied 403"]},
        "bundle_exclusions_verified": True,
        "restore_snapshot_records": restore["engines"]["mongodb"]["restored"]["records"],
        "chatgpt_account_connected": False,
        "infrastructure_recreated": False,
        "limits": ["No Terraform apply/destroy or VM recreation", "No clean-host or bit-identical rebuild guarantee", "Four native healthchecks deferred to authorized recreation; external probes run now", "ChatGPT owner connection and Billing budget IAM remain external"],
    }
    result["evidence_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.iterdir() if p.is_file() and p.suffix in (".json", ".log", ".xml", ".txt") and p.name not in ("summary.json", "finalize.log") and not p.name.endswith("_raw.log")}
    (BASE / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "evidence_sha256"}, indent=2))


if __name__ == "__main__":
    main()
