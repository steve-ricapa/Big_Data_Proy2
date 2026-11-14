"""Airflow 3 scheduler execution with a real failed Neo4j connection and retry.

Run only when the ETL is idle. Output contains state, not credentials/log bodies.
"""

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from airflow.models import DagRun, TaskInstance
from airflow.utils.session import create_session

dag_id = "nvd_threat_intelligence"
parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=10000, help="0 processes all local records")
args = parser.parse_args()
if args.limit < 0:
    parser.error("limit must be >= 0")
run_id = ("full34_" if args.limit == 0 else "migration34_") + datetime.now(UTC).strftime("%Y%m%dT%H%M%S")


def cli(*args):
    result = subprocess.run(["airflow", "dags", *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Airflow CLI failed: " + args[0])


cli("unpause", dag_id)
try:
    cli("trigger", dag_id, "--run-id", run_id, "--conf", json.dumps({"limit": args.limit, "fail_neo4j_once": True}))
    timeout = 1800 if args.limit == 0 else 600
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with create_session() as session:
            run = session.query(DagRun).filter_by(dag_id=dag_id, run_id=run_id).one_or_none()
            if run and run.state in ("success", "failed"):
                tasks = [
                    {"task_id": t.task_id, "state": t.state, "try_number": t.try_number}
                    for t in session.query(TaskInstance).filter_by(dag_id=dag_id, run_id=run_id).all()
                ]
                result = {"version": "3.4.0", "run_id": run_id, "limit": args.limit, "state": run.state, "tasks": tasks}
                name = "airflow34_full.json" if args.limit == 0 else "airflow34_scheduler_retry.json"
                Path("/opt/project/evidence", name).write_text(json.dumps(result, indent=2), encoding="utf-8")
                print(json.dumps(result), flush=True)
                assert run.state == "success", result
                assert len(tasks) == 7 and all(t["state"] == "success" for t in tasks)
                assert next(t for t in tasks if t["task_id"] == "load_neo4j")["try_number"] >= 2
                break
        time.sleep(5)
    else:
        raise TimeoutError(f"Airflow 3 did not finish within {timeout} seconds")
finally:
    cli("pause", dag_id)
