"""NVD daily replay: only artifact paths travel through XCom (Airflow 2/3)."""

import hashlib
from datetime import timedelta

import pendulum

try:
    from airflow.sdk import Param, dag, get_current_context, task
except ImportError:  # Preserve the isolated, verified Airflow 2 baseline.
    from airflow.decorators import dag, task
    from airflow.models.param import Param
    from airflow.operators.python import get_current_context


@dag(
    dag_id="nvd_threat_intelligence",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={
        "owner": "bigdata",
        "retries": 2,
        "retry_delay": timedelta(seconds=30),
        "retry_exponential_backoff": True,
    },
    params={
        "limit": Param(1000, type="integer", minimum=0),
        "fail_neo4j_once": Param(False, type="boolean"),
        "source_mode": Param("auto", enum=["auto", "local", "nvd"]),
    },
    tags=["nvd", "bigdata", "incremental"],
)
def nvd_pipeline():
    @task
    def extract():
        from threat_intelligence.common.config import settings
        from threat_intelligence.pipeline import prepare

        context = get_current_context()
        suffix = hashlib.sha256(context["run_id"].encode()).hexdigest()[:20]
        mode = context["params"]["source_mode"]
        scheduled = str(context["dag_run"].run_type) in ("scheduled", "DagRunType.SCHEDULED")
        if mode == "nvd" or (mode == "auto" and scheduled):
            from threat_intelligence.ingestion.sync import prepare_sync

            return prepare_sync(settings().staging_dir / suffix, settings().state_dir)
        return prepare(settings().staging_dir / suffix, int(context["params"]["limit"]))

    @task
    def validate(path):
        from threat_intelligence.pipeline import validate as execute

        execute(path)
        return path

    @task
    def load_mongodb(path):
        from threat_intelligence.pipeline import load

        load(path, "mongodb")
        return path

    @task
    def load_cassandra(path):
        from threat_intelligence.pipeline import load

        load(path, "cassandra")
        return path

    @task
    def load_neo4j(path):
        from pathlib import Path

        from threat_intelligence.common.config import settings
        from threat_intelligence.databases.neo4j import Neo
        from threat_intelligence.pipeline import load

        # Explicit opt-in resilience exercise; never enabled for normal runs.
        marker = Path(path) / "injected_neo4j_failure.once"
        if get_current_context()["params"]["fail_neo4j_once"] and not marker.exists():
            marker.touch()
            broken = Neo(settings().model_copy(update={"neo4j_uri": "bolt://neo4j:1"}))
            try:
                broken.ping()  # Real refused connection; Airflow must retry this task.
            finally:
                broken.close()
            raise RuntimeError("Expected test connection to be refused")
        load(path, "neo4j")
        return path

    @task
    def calculate_kpis(path):
        from threat_intelligence.pipeline import kpis

        kpis(path)
        return path

    @task
    def verify(path):
        from threat_intelligence.common.config import settings
        from threat_intelligence.ingestion.sync import commit_sync
        from threat_intelligence.pipeline import verify as execute

        result = execute(path)
        commit_sync(path, settings().state_dir)
        return result

    verify(
        calculate_kpis(load_neo4j(load_cassandra(load_mongodb(validate(extract())))))
    )


nvd_pipeline()
