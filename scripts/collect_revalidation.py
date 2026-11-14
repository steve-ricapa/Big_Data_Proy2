"""Collect existing execution artifacts; never turns absent evidence into PASS."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

evidence = Path("docs/evidence")


def read(name):
    return json.loads((evidence / name).read_text(encoding="utf-8"))


def suite(name):
    root = ET.parse(evidence / name).getroot()
    cases = list(root.iter("testcase"))
    failed = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    return {"tests": len(cases), "passed": len(cases) - failed - skipped, "failed": failed, "skipped": skipped}


def audit(name):
    dependencies = read(name)["dependencies"]
    return {"packages": len(dependencies), "known_findings": sum(len(d.get("vulns", [])) for d in dependencies)}


run = read("airflow34_scheduler_retry.json")
run_dir = hashlib.sha256(run["run_id"].encode()).hexdigest()[:20]
manifest = json.loads((Path("data/staging") / run_dir / "run.json").read_text(encoding="utf-8"))
plan = (evidence / "revalidation_terraform_plan.txt").read_text(encoding="utf-8")
match = re.search(r"Plan: (\d+) to add, (\d+) to change, (\d+) to destroy", plan)
assert match, "No successful Terraform plan summary"
result = {
    "collected_at": datetime.now(UTC).isoformat(),
    "dataset_inventory": read("revalidation_inventory.json"),
    "engine_verification": manifest["stages"]["verify"],
    "docker_pytest": suite("revalidation_integration_tests.xml"),
    "windows_pytest": suite("revalidation_unit_tests.xml"),
    "airflow": run,
    "airflow_audit": audit("airflow34_dependency_audit.json"),
    "app_mcp_audit": audit("mcp_dependency_audit.json"),
    "incremental": read("revalidation_incremental.json"),
    "kpis": read("revalidation_kpi_audit.json"),
    "mcp": read("mcp_validation.json"),
    "terraform_plan": dict(zip(("add", "change", "destroy"), map(int, match.groups()), strict=True)),
    "cloud_deployed": False,
    "cloud_apply_executed": False,
    "limitations": ["No full Airflow run: 10000 input sample, canonical stores contain 171791", "No production TLS/HA or remote ChatGPT connector", "No distributed transaction or concurrent pipeline guarantee"],
}
if (evidence / "airflow34_full.json").exists():
    full = read("airflow34_full.json")
    full_dir = hashlib.sha256(full["run_id"].encode()).hexdigest()[:20]
    full_manifest = json.loads((Path("data/staging") / full_dir / "run.json").read_text(encoding="utf-8"))
    result["airflow_full"] = {**full, "stages": full_manifest["stages"]}
    if full["state"] == "success":
        assert full_manifest["stages"]["validate"]["unique_valid"] == 171791
        result["engine_verification"] = full_manifest["stages"]["verify"]
        result["limitations"] = result["limitations"][1:]
(evidence / "revalidation_state.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"counts": result["engine_verification"]["counts"], "tests": result["docker_pytest"], "airflow": run["state"], "terraform": result["terraform_plan"]}))
