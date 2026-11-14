"""Trigger a cloud DAG run with explicit conf and capture state, stages and sync journal.

Runs inside the airflow3-scheduler container. Output contains states and metrics
only, never credentials or token material.
"""

import argparse
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from airflow.models import DagRun, TaskInstance
from airflow.utils.session import create_session

dag_id = "nvd_threat_intelligence"
parser = argparse.ArgumentParser()
parser.add_argument("--label", default="sync34")
parser.add_argument("--conf", default='{"source_mode":"nvd","limit":0,"fail_neo4j_once":false}')
parser.add_argument("--leave-unpaused", action="store_true")
args = parser.parse_args()
run_id = args.label + "_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S")


def cli(*argv):
    result = subprocess.run(["airflow", "dags", *argv], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Airflow CLI failed: " + argv[0])


cli("unpause", dag_id)
try:
    cli("trigger", dag_id, "--run-id", run_id, "--conf", args.conf)
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        with create_session() as session:
            run = session.query(DagRun).filter_by(dag_id=dag_id, run_id=run_id).one_or_none()
            if run and run.state in ("success", "failed"):
                tasks = [
                    {"task_id": t.task_id, "state": t.state, "try_number": t.try_number}
                    for t in session.query(TaskInstance).filter_by(dag_id=dag_id, run_id=run_id).all()
                ]
                suffix = hashlib.sha256(run_id.encode()).hexdigest()[:20]
                run_dir = Path("/opt/project/data/staging") / suffix
                outcome = {"run_id": run_id, "state": run.state, "tasks": tasks, "run_dir": str(run_dir)}
                stages = run_dir / "run.json"
                if stages.exists():
                    outcome["stages"] = json.loads(stages.read_text(encoding="utf-8"))["stages"]
                journal = run_dir / "nvd_sync" / "download.json"
                if journal.exists():
                    outcome["nvd_sync"] = json.loads(journal.read_text(encoding="utf-8"))
                print(json.dumps(outcome, indent=2), flush=True)
                assert run.state == "success", run.state
                assert len(tasks) == 7 and all(t["state"] == "success" for t in tasks)
                break
        time.sleep(5)
    else:
        raise TimeoutError("DAG run did not finish within 1800 seconds")
finally:
    if not args.leave_unpaused:
        cli("pause", dag_id)
