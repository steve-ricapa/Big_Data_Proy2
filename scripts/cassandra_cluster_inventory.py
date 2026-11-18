"""Read-only CVE fingerprints and Cassandra sample/projection checks from Airflow."""

import hashlib
import json
import time
from datetime import UTC, datetime

from threat_intelligence.common.config import settings
from threat_intelligence.databases.cassandra import Cassandra
from threat_intelligence.databases.mongodb import Mongo
from threat_intelligence.databases.neo4j import Neo


def fingerprint(rows):
    total = count = 0
    identities = set()
    for cve_id, content_hash in rows:
        total += int.from_bytes(hashlib.sha256(f"{cve_id}:{content_hash}".encode()).digest())
        count += 1
        identities.add(cve_id)
    return {"records": count, "duplicates": count - len(identities), "sha256_sum": f"{total % (1 << 256):064x}"}


def main():
    result = {"at": datetime.now(UTC).isoformat(), "engines": {}}
    for name in ("mongodb", "cassandra", "neo4j"):
        start = time.perf_counter()
        if name == "cassandra":
            engine = Cassandra(settings(), initialize_schema=False)
        elif name == "mongodb":
            engine = Mongo(settings())
        else:
            engine = Neo(settings())
        try:
            if name == "mongodb":
                rows = ((r["cve_id"], r["content_hash"]) for r in engine.collection.find({}, {"_id": 0, "cve_id": 1, "content_hash": 1}))
                kpis = engine.db.kpis.find_one({"_id": "latest"}, {"_id": 0})
                result["kpis"] = {k: kpis[k] for k in ("as_of", "total_cves", "severity", "graph", "modified_last_30_days", "unique_affected_products")}
            elif name == "cassandra":
                execute = engine.session.execute
                result["replication"] = {r.keyspace_name: dict(r.replication) for r in execute("SELECT keyspace_name, replication FROM system_schema.keyspaces")}
                result["columns"] = [r._asdict() for r in execute("SELECT table_name,column_name,kind,position,type,clustering_order FROM system_schema.columns WHERE keyspace_name=%s", (engine.keyspace,))]
                result["samples"] = [r._asdict() for r in execute("SELECT cve_id,content_hash FROM cves_by_id WHERE cve_id IN ('CVE-2024-0001','CVE-2021-44228')")]
                result["snapshot_matches"] = json.loads(execute("SELECT payload FROM kpi_snapshots WHERE snapshot_id='latest'").one().payload) == kpis
                rows = ((r.cve_id, r.content_hash) for r in execute("SELECT cve_id,content_hash FROM cves_by_id"))
            else:
                rows = ((r["id"], r["hash"]) for r in engine.query("MATCH (c:CVE) RETURN c.id AS id,c.content_hash AS hash"))
                result["graph_control_edges"] = engine.query("MATCH (:CVE {id:'CVE-2021-44228'})-[r]->() RETURN count(r) AS edges")[0]["edges"]
            result["engines"][name] = {**fingerprint(rows), "elapsed_s": round(time.perf_counter() - start, 3)}
        finally:
            engine.close()
    print(json.dumps(result, indent=2))
    assert len({(r["records"], r["sha256_sum"]) for r in result["engines"].values()}) == 1
    assert not any(r["duplicates"] for r in result["engines"].values()) and result["snapshot_matches"]


if __name__ == "__main__":
    main()
