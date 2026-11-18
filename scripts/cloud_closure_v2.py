"""Run the authorized closure CRUD/regression on the existing VM only."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/opt/threat-intelligence")
OUT = ROOT / "docs/evidence/acceptance_v2"
COMPOSE = ["bash", str(ROOT / "scripts/cloud_compose.sh")]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    OUT.chmod(0o770)  # Tester UID50000 uses GID0 to write JUnit, not production data.
    guard = "from airflow.models import DagRun;from airflow.utils.session import create_session;\nwith create_session() as s: assert s.query(DagRun).filter(DagRun.state.in_(['queued','running'])).count()==0"
    subprocess.run(["docker", "exec", "threat-intelligence-airflow3-scheduler-1", "python", "-c", guard], check=True)
    active = subprocess.run(["systemctl", "show", "ti-backup.service", "--property=ActiveState", "--value"], capture_output=True, text=True, check=True).stdout.strip()
    assert active not in ("active", "activating"), "Backup is running"
    if sys.argv[1] == "crud":
        code = "import json;from threat_intelligence.crud import run_crud;print(json.dumps(run_crud()))"
        p = subprocess.run(["docker", "exec", "threat-intelligence-airflow3-scheduler-1", "python", "-c", code], capture_output=True, text=True, check=False)
        if p.returncode:
            raise RuntimeError("Cloud CRUD failed; driver output suppressed")
        result = json.loads(p.stdout.splitlines()[-1])
        (OUT / "crud.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
    else:
        # Use the existing test image and current source/tests, not stale layers.
        override = OUT / "verification-image.json"
        override.write_text(json.dumps({"services": {"tester": {"image": "ti-v2-test:verification"}}}))
        args = [*COMPOSE, "run", "--rm", "--no-deps", "-v", f"{ROOT / 'src'}:/app/src:ro", "-v", f"{ROOT / 'tests'}:/app/tests:ro", "tester", "-q", "-p", "no:cacheprovider", "--junitxml=/app/docs/evidence/acceptance_v2/cloud_tests.xml"]
        if len(sys.argv) > 2 and sys.argv[2] == "rebuilt":
            args = [*COMPOSE, "-f", str(override), *args[len(COMPOSE):]]
        with (OUT / "cloud_tests.log").open("w") as log:
            p = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        print(json.dumps({"at": datetime.now(UTC).isoformat(), "exit_code": p.returncode, "log": str(OUT / "cloud_tests.log")}))
        return p.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
