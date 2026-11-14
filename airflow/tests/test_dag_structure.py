"""Run inside the Airflow image, not native Windows Python."""

from itertools import pairwise


def check():
    from airflow.models import DagBag
    from airflow.utils.dag_cycle_tester import check_cycle

    bag = DagBag(dag_folder="/opt/airflow/dags", include_examples=False)
    assert not bag.import_errors, bag.import_errors
    dag = bag.get_dag("nvd_threat_intelligence")
    assert dag is not None
    assert len(dag.tasks) == 7
    check_cycle(dag)
    expected = [
        "extract",
        "validate",
        "load_mongodb",
        "load_cassandra",
        "load_neo4j",
        "calculate_kpis",
        "verify",
    ]
    for first, second in pairwise(expected):
        assert second in dag.get_task(first).downstream_task_ids
    assert all(t.retries == 2 for t in dag.tasks)
    assert dag.max_active_runs == 1
    print("PASS: DAG imports, 7 tasks, acyclic chain, 2 retries, max_active_runs=1")


if __name__ == "__main__":
    check()
