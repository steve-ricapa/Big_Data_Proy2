"""Unpause the DAG so an in-flight run's pending tasks get scheduled, then wait.

Does not trigger anything new; reads states only. Exits non-zero on failure.
"""

import json
import subprocess
import sys
import time

from airflow.models import DagRun, TaskInstance
from airflow.utils.session import create_session

dag_id = "nvd_threat_intelligence"
run_id = sys.argv[1]
deadline = time.monotonic() + 2700


def cli(*argv):
    result = subprocess.run(["airflow", "dags", *argv], capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Airflow CLI failed: " + argv[0])


cli("unpause", dag_id)
while time.monotonic() < deadline:
    with create_session() as session:
        run = session.query(DagRun).filter_by(dag_id=dag_id, run_id=run_id).one_or_none()
        if run and run.state in ("success", "failed"):
            tasks = [
                {"task_id": t.task_id, "state": t.state, "try_number": t.try_number}
                for t in session.query(TaskInstance).filter_by(dag_id=dag_id, run_id=run_id).all()
            ]
            print(json.dumps({"run_id": run_id, "state": run.state, "tasks": tasks}), flush=True)
            raise SystemExit(0 if run.state == "success" else 1)
    time.sleep(10)
raise TimeoutError("run did not finish within 2700 seconds")
