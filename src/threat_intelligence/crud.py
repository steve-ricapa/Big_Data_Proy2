"""Isolated actual-engine CRUD; never deletes an existing CVE."""

import uuid
from datetime import UTC, datetime

from threat_intelligence.common.config import settings
from threat_intelligence.databases.cassandra import Cassandra
from threat_intelligence.pipeline import connect
from threat_intelligence.transformations.normalize import normalize


def run_crud(engines=("mongodb", "cassandra", "neo4j")):
    identifier = "CVE-2099-" + str(uuid.uuid4().int)[:18]
    row = normalize(
        {
            "id": identifier,
            "published": "2099-01-01T00:00:00Z",
            "lastModified": "2099-01-01T00:00:00Z",
            "descriptions": [{"lang": "en", "value": "Isolated CRUD test"}],
        }
    )
    results = {"at": datetime.now(UTC).isoformat(), "id": identifier, "engines": {}}
    for engine in engines:
        # Production probes must not initialize or alter existing schemas.
        sink = Cassandra(settings(), initialize_schema=False) if engine == "cassandra" else connect(engine)
        created = False
        mongo_id = None
        try:
            if engine == "mongodb":
                assert sink.collection.find_one({"cve_id": identifier}) is None
                mongo_id = sink.collection.insert_one(dict(row)).inserted_id
                created = True
                assert (
                    sink.collection.find_one({"cve_id": identifier})["description"]
                    == row["description"]
                )
                sink.collection.update_one(
                    {"cve_id": identifier}, {"$set": {"description": "Updated CRUD"}}
                )
                assert (
                    sink.collection.find_one({"cve_id": identifier})["description"]
                    == "Updated CRUD"
                )
                sink.collection.delete_one({"_id": mongo_id, "cve_id": identifier})
                assert sink.collection.find_one({"cve_id": identifier}) is None
            elif engine == "cassandra":
                session = sink.session
                select = session.prepare(
                    "SELECT document FROM cves_by_id WHERE cve_id=?"
                )
                assert session.execute(select, (identifier,)).one() is None
                inserted = session.execute(
                    session.prepare("INSERT INTO cves_by_id (cve_id,content_hash,document) VALUES (?,?,?) IF NOT EXISTS USING TTL 600"),
                    (identifier, "crud", "Created CRUD"),
                ).one()
                assert inserted.applied, "Temporary ID already exists; refusing overwrite"
                created = True
                assert (
                    session.execute(select, (identifier,)).one().document
                    == "Created CRUD"
                )
                session.execute(
                    session.prepare("UPDATE cves_by_id USING TTL 600 SET document=? WHERE cve_id=?"),
                    ("Updated CRUD", identifier),
                )
                assert (
                    session.execute(select, (identifier,)).one().document
                    == "Updated CRUD"
                )
                session.execute(
                    session.prepare("DELETE FROM cves_by_id WHERE cve_id=?"),
                    (identifier,),
                )
                assert session.execute(select, (identifier,)).one() is None
            else:
                assert not sink.query(
                    "MATCH (c:CVE {id:$id}) RETURN c.id", id=identifier
                )
                sink.query(
                    "CREATE (c:CVE {id:$id, acceptance_probe:$id, description:'Created CRUD'})", id=identifier
                )
                created = True
                assert (
                    sink.query(
                        "MATCH (c:CVE {id:$id}) RETURN c.description AS v",
                        id=identifier,
                    )[0]["v"]
                    == "Created CRUD"
                )
                sink.query(
                    "MATCH (c:CVE {id:$id}) SET c.description='Updated CRUD'",
                    id=identifier,
                )
                assert (
                    sink.query(
                        "MATCH (c:CVE {id:$id}) RETURN c.description AS v",
                        id=identifier,
                    )[0]["v"]
                    == "Updated CRUD"
                )
                sink.query("MATCH (c:CVE {id:$id}) DETACH DELETE c", id=identifier)
                assert not sink.query(
                    "MATCH (c:CVE {id:$id}) RETURN c.id", id=identifier
                )
            results["engines"][engine] = {
                op: "PASS" for op in ("create", "read", "update", "delete")
            }
        finally:
            try:
                # Clean only an identity that this invocation actually created,
                # even if an intermediate assertion or driver operation failed.
                if created:
                    if engine == "mongodb":
                        sink.collection.delete_one({"_id": mongo_id, "cve_id": identifier})
                        assert sink.collection.find_one({"cve_id": identifier}) is None
                    elif engine == "cassandra":
                        sink.session.execute(
                            sink.session.prepare("DELETE FROM cves_by_id WHERE cve_id=? IF content_hash=?"),
                            (identifier, "crud"),
                        )
                        assert sink.session.execute(select, (identifier,)).one() is None
                    else:
                        sink.query("MATCH (c:CVE {id:$id, acceptance_probe:$id}) DELETE c", id=identifier)
                        assert not sink.query("MATCH (c:CVE {id:$id}) RETURN c.id", id=identifier)
            finally:
                sink.close()
    results["cleanup_verified"] = True
    return results
