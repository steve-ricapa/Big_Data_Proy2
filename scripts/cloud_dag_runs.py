"""List recent DAG runs and their task states (read-only)."""

import json

from airflow.models import DagRun, TaskInstance
from airflow.utils.session import create_session

with create_session() as session:
    runs = session.query(DagRun).filter_by(dag_id="nvd_threat_intelligence").order_by(DagRun.id.desc()).limit(6).all()
    out = []
    for run in runs:
        tasks = [
            {"task_id": t.task_id, "state": t.state, "try": t.try_number}
            for t in session.query(TaskInstance).filter_by(dag_id="nvd_threat_intelligence", run_id=run.run_id).all()
        ]
        out.append({"run_id": run.run_id, "state": run.state, "queued": run.queued_at.isoformat() if run.queued_at else None, "tasks": tasks})
print(json.dumps(out, indent=1, default=str))
