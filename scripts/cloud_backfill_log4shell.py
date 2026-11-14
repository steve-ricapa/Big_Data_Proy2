"""Explicit one-CVE NVD backfill, coordinated with Airflow; no OAuth changes.

Run only inside the existing scheduler after the outer operator checks that
backup is inactive and a source with the pinned digest has been staged.
"""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from airflow.models import DagModel, DagRun
from airflow.utils.session import create_session

from threat_intelligence import pipeline
from threat_intelligence.common.config import settings
from threat_intelligence.databases.cassandra import Cassandra
from threat_intelligence.databases.mongodb import Mongo
from threat_intelligence.databases.neo4j import Neo
from threat_intelligence.transformations.normalize import normalize

DAG = "nvd_threat_intelligence"
IDENTIFIER = "CVE-2021-44228"
SOURCE = Path("/opt/project/data/raw/nvd/backfill/nvdcve-2.0-CVE-2021-44228.json")
EXPECTED_SHA256 = "58671756e1d6de00aac65a9dd316cd912976e2695adebe21083a2558701d180f"


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA256
    data = json.loads(SOURCE.read_text())
    assert data["totalResults"] == len(data["vulnerabilities"]) == 1
    canonical = normalize(data["vulnerabilities"][0])
    assert canonical["cve_id"] == IDENTIFIER
    config = settings()
    watermark = config.state_dir / "nvd_sync.json"
    watermark_before = hashlib.sha256(watermark.read_bytes()).hexdigest()
    mongo, cass, neo = Mongo(config), Cassandra(config, initialize_schema=False), Neo(config)
    try:
        assert mongo.collection.find_one({"cve_id": IDENTIFIER}) is None, "Existing data: review before retry"
        assert cass.session.execute("SELECT cve_id FROM cves_by_id WHERE cve_id=%s", (IDENTIFIER,)).one() is None
        assert not neo.query("MATCH (c:CVE {id:$id}) RETURN c.id AS id", id=IDENTIFIER)
        before_total = mongo.collection.count_documents({}, hint="cve_id_1")
        before_snapshot = mongo.db.kpis.find_one({"_id": "latest"}, {"_id": 0})
    finally:
        mongo.close()
        cass.close()
        neo.close()
    with create_session() as session:
        dag = session.query(DagModel).filter_by(dag_id=DAG).one()
        previous_paused = dag.is_paused
        assert previous_paused is False, "Expected active DAG; do not override external pause"
        dag.is_paused = True
    run_dir = config.staging_dir / ("backfill_log4shell_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S"))
    try:
        with create_session() as session:
            assert session.query(DagRun).filter(DagRun.dag_id == DAG, DagRun.state.in_(["queued", "running"])).count() == 0, "ETL is active"
        pipeline.prepare(run_dir, sources=[str(SOURCE)])
        (run_dir / "kpis_before.json").write_text(json.dumps(before_snapshot, indent=2))
        valid = pipeline.validate(run_dir)
        assert valid["unique_valid"] == 1 and valid["invalid"] == 0
        for engine in ("mongodb", "cassandra", "neo4j"):
            loaded = pipeline.load(run_dir, engine)
            assert loaded["seen"] == loaded["new"] == loaded["written"] == 1
            assert loaded["total_in_engine"] == before_total + 1
        kpis = pipeline.kpis(run_dir)
        assert kpis["total_cves"] == before_total + 1
        counts = pipeline.verify(run_dir)
        assert set(counts.values()) == {before_total + 1}
        assert hashlib.sha256(watermark.read_bytes()).hexdigest() == watermark_before
        result = {
            "at": datetime.now(UTC).isoformat(), "status": "PASS", "cve_id": IDENTIFIER,
            "source_sha256": EXPECTED_SHA256, "canonical_hash": canonical["content_hash"],
            "before_total": before_total, "after_counts": counts, "run_dir": str(run_dir),
            "cvss": canonical["cvss"], "product_count": len(canonical["products"]),
            "cpe_count": len(canonical["cpes"]), "nvd_watermark_unchanged": True,
        }
    finally:
        with create_session() as session:
            session.query(DagModel).filter_by(dag_id=DAG).one().is_paused = previous_paused
    result["dag_active_restored"] = not previous_paused
    (run_dir / "backfill_result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
