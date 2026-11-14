"""Foreground actual-scheduler resilience test, run inside Airflow after ETL is idle.

The only injected fault is a connection to a deliberately closed Neo4j port.
"""

import json
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from airflow.models import DagRun
from airflow.utils.session import create_session

dag_id = "nvd_threat_intelligence"
run_id = "resilience_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
subprocess.run(["airflow", "dags", "unpause", dag_id], check=True, capture_output=True)
try:
    subprocess.run(
        [
            "airflow",
            "dags",
            "trigger",
            dag_id,
            "--run-id",
            run_id,
            "--conf",
            '{"limit":10000,"fail_neo4j_once":true}',
        ],
        check=True,
        capture_output=True,
    )
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        with create_session() as session:
            run = (
                session.query(DagRun)
                .filter(DagRun.dag_id == dag_id, DagRun.run_id == run_id)
                .one_or_none()
            )
            if run and run.state in ("success", "failed"):
                tasks = [
                    {
                        "task_id": task.task_id,
                        "state": task.state,
                        "try_number": task.try_number,
                        "attempts": task.prev_attempted_tries,
                    }
                    for task in run.get_task_instances(session=session)
                ]
                result = {
                    "dag_id": dag_id,
                    "run_id": run_id,
                    "state": run.state,
                    "limit": 10000,
                    "injected_fault": "Neo4j closed port once",
                    "tasks": tasks,
                }
                Path("/opt/project/evidence/scheduler_retry.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
                log_dir = (
                    Path("/opt/airflow/logs")
                    / f"dag_id={dag_id}"
                    / f"run_id={run_id}"
                    / "task_id=load_neo4j"
                )
                for log in log_dir.glob("attempt=*.log"):
                    shutil.copyfile(
                        log,
                        Path("/opt/project/evidence") / ("airflow_retry_" + log.name),
                    )
                assert run.state == "success", result
                assert len(tasks) == 7 and all(t["state"] == "success" for t in tasks)
                assert (
                    next(t for t in tasks if t["task_id"] == "load_neo4j")["attempts"]
                    >= 2
                )
                print(json.dumps(result), flush=True)
                break
        time.sleep(5)
    else:
        raise TimeoutError("Scheduler did not finish resilience test in 360 seconds")
finally:
    # Do not leave a daily workload unexpectedly enabled after the demonstration.
    subprocess.run(
        ["airflow", "dags", "pause", dag_id], check=True, capture_output=True
    )
