"""Real-engine incremental regression using a clearly synthetic, isolated CVE."""

import copy
import uuid

from threat_intelligence import pipeline
from threat_intelligence.common.config import settings
from threat_intelligence.common.io import write_json
from threat_intelligence.incremental.state import State
from threat_intelligence.transformations.normalize import normalize


def run_selftest():
    identifier = "CVE-2099-" + str(uuid.uuid4().int)[:18]
    root = settings().state_dir / "selftest" / identifier
    root.mkdir(parents=True)
    cve = {
        "id": identifier,
        "published": "2099-01-01T00:00:00Z",
        "lastModified": "2099-01-01T00:00:00Z",
        "descriptions": [{"lang": "en", "value": "SYNTHETIC INCREMENTAL TEST"}],
        "metrics": {
            "cvssMetricV31": [{"cvssData": {"baseScore": 9.8, "version": "3.1"}}]
        },
        "weaknesses": [{"description": [{"value": "CWE-79"}]}],
    }
    original = copy.deepcopy(cve)
    results = {"synthetic_id": identifier, "checks": {}}
    projections = []

    def execute(name, entries):
        source = root / (name + ".json")
        write_json(source, {"vulnerabilities": [{"cve": entry} for entry in entries]})
        run = root / name
        pipeline.prepare(run, sources=[source])
        pipeline.validate(run)
        for engine in ("mongodb", "cassandra", "neo4j"):
            pipeline.load(run, engine)
        return pipeline.manifest(run)["stages"]

    try:
        projections.append(normalize(cve))
        first = execute("initial", [cve, {"id": "INVALID"}])
        assert first["validate"]["invalid"] == 1
        for engine in ("mongodb", "cassandra", "neo4j"):
            assert first[engine]["new"] == 1
        results["checks"]["new_and_invalid"] = "PASS"
        replay = execute("replay", [cve])
        assert all(
            replay[e]["unchanged"] == 1 for e in ("mongodb", "cassandra", "neo4j")
        )
        results["checks"]["unchanged_replay"] = "PASS"
        cve["lastModified"] = "2099-01-02T00:00:00Z"
        cve["metrics"]["cvssMetricV31"][0]["cvssData"]["baseScore"] = 2.0
        cve["weaknesses"] = []
        projections.append(normalize(cve))
        modified = execute("modified", [cve])
        assert all(
            modified[e]["modified"] == 1 for e in ("mongodb", "cassandra", "neo4j")
        )
        cassandra = pipeline.connect("cassandra")
        try:
            query = cassandra.session.prepare(
                "SELECT cve_id FROM cves_by_severity WHERE bucket=? AND month=? AND published=? AND cve_id=?"
            )
            old = projections[0]
            assert (
                cassandra.session.execute(
                    query, ("CRITICAL", old["month"], old["published"], identifier)
                ).one()
                is None
            )
        finally:
            cassandra.close()
        neo = pipeline.connect("neo4j")
        try:
            assert (
                neo.query(
                    "MATCH (c:CVE {id:$id})-[r:CLASSIFIED_AS]->() RETURN count(r) AS n",
                    id=identifier,
                )[0]["n"]
                == 0
            )
        finally:
            neo.close()
        results["checks"]["modified_removes_stale_partitions_and_edges"] = "PASS"
        stale = execute("stale", [original])
        assert all(stale[e]["stale"] == 1 for e in ("mongodb", "cassandra", "neo4j"))
        results["checks"]["older_update_rejected"] = "PASS"
        pipeline.verify(root / "stale")
        results["checks"]["all_engine_content_parity"] = "PASS"
    finally:
        for engine in ("mongodb", "cassandra", "neo4j"):
            sink = pipeline.connect(engine)
            try:
                if engine == "mongodb":
                    sink.collection.delete_one({"cve_id": identifier})
                elif engine == "neo4j":
                    sink.query("MATCH (c:CVE {id:$id}) DETACH DELETE c", id=identifier)
                else:
                    for row in projections:
                        for table, *key in sink.keys(row):
                            sink.session.execute(sink.deletes[table], tuple(key))
                    sink.session.execute(
                        sink.session.prepare("DELETE FROM cves_by_id WHERE cve_id=?"),
                        (identifier,),
                    )
            finally:
                sink.close()
        state = State(settings().state_dir / "checkpoints.sqlite")
        with state.db:
            state.db.execute("DELETE FROM checkpoints WHERE id=?", (identifier,))
        state.close()
    return results
