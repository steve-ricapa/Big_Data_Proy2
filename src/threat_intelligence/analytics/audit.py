"""Independent database-side aggregation check of persisted KPI snapshots."""

import json

from threat_intelligence.pipeline import connect


def audit_kpis():
    mongo = connect("mongodb")
    try:
        snapshot = mongo.db.kpis.find_one({"_id": "latest"}, {"_id": 0})
        if snapshot is None:
            raise ValueError("No KPI snapshot")
        collection = mongo.collection
        assert collection.count_documents({}) == snapshot["total_cves"]
        checks = {"total_cves": "PASS"}
        for field, key in (("severity", "severity"), ("month", "monthly")):
            grouped = {
                r["_id"]: r["n"]
                for r in collection.aggregate(
                    [{"$group": {"_id": "$" + field, "n": {"$sum": 1}}}]
                )
            }
            assert grouped == snapshot[key], (field, grouped, snapshot[key])
            checks[key] = "PASS"
        scores = {
            r["_id"]: {"count": r["n"], "average": round(r["average"], 4)}
            for r in collection.aggregate(
                [
                    {"$match": {"cvss": {"$ne": None}}},
                    {
                        "$group": {
                            "_id": "$cvss.version",
                            "n": {"$sum": 1},
                            "average": {"$avg": "$cvss.score"},
                        }
                    },
                ]
            )
        }
        assert scores == snapshot["cvss_by_version"]
        checks["cvss_by_version"] = "PASS"
        product_count = next(
            collection.aggregate(
                [
                    {"$unwind": "$products"},
                    {"$group": {"_id": "$products.id"}},
                    {"$count": "n"},
                ],
                allowDiskUse=True,
            ),
            {"n": 0},
        )["n"]
        assert product_count == snapshot["unique_affected_products"]
        checks["unique_affected_products"] = "PASS"
        for field, key in (("cwes", "top_cwes"), ("products.id", "top_products")):
            # Audit each ranked entry with independent Mongo count query.
            for identity, count in snapshot[key]:
                assert collection.count_documents({field: identity}) == count
            checks[key] = "PASS"
        cassandra = connect("cassandra")
        try:
            result = cassandra.session.execute(
                "SELECT payload FROM kpi_snapshots WHERE snapshot_id='latest'"
            ).one()
            assert json.loads(result.payload) == snapshot
            checks["cassandra_snapshot_equals_mongo"] = "PASS"
        finally:
            cassandra.close()
        graph = connect("neo4j")
        try:
            assert (
                graph.query("MATCH (n) RETURN count(n) AS n")[0]["n"]
                == snapshot["graph"]["nodes"]
            )
            assert (
                graph.query("MATCH ()-[r]->() RETURN count(r) AS n")[0]["n"]
                == snapshot["graph"]["relationships"]
            )
            checks["graph_counts"] = "PASS"
        finally:
            graph.close()
        return {
            "as_of": snapshot["as_of"],
            "total_cves": snapshot["total_cves"],
            "checks": checks,
        }
    finally:
        mongo.close()
