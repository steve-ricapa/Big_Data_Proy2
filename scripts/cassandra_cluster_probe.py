"""A bounded TTL probe of quorum writes/reads using the deployed Airflow client."""

import argparse
import json
import time
from datetime import UTC, datetime

from cassandra import ConsistencyLevel

from threat_intelligence.common.config import settings
from threat_intelligence.databases.cassandra import Cassandra


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("write", "read-all", "delete"))
    p.add_argument("marker", choices=("before-fault", "during-node2-fault", "during-node3-fault"))
    args = p.parse_args()
    config = settings()
    assert config.cassandra_consistency == "LOCAL_QUORUM" and not config.cassandra_create_keyspace
    key = f"ti-cluster-acceptance-{args.marker}"
    db = Cassandra(config, initialize_schema=False)
    start = time.perf_counter()
    try:
        session = db.session
        if args.mode == "write":
            statement = session.prepare("INSERT INTO cves_by_id (cve_id,content_hash,document) VALUES (?, ?, ?) IF NOT EXISTS USING TTL 1800")
            response = session.execute(statement, (key, "quorum-probe", '{"test":true}'))
            assert response.was_applied, "Probe key already exists; no real row modified"
            coordinator = response.response_future.coordinator_host.address
        elif args.mode == "delete":
            result = session.execute(session.prepare("DELETE FROM cves_by_id WHERE cve_id=? IF content_hash='quorum-probe'"), (key,))
            assert result.was_applied
            coordinator = result.response_future.coordinator_host.address
        if args.mode != "delete":
            read = session.prepare("SELECT content_hash, document, writetime(document) AS written_us, ttl(document) AS ttl FROM cves_by_id WHERE cve_id=?")
            if args.mode == "read-all":
                read.consistency_level = ConsistencyLevel.ALL
            response = session.execute(read, (key,))
            row = response.one()
            assert row.content_hash == "quorum-probe" and row.document == '{"test":true}' and 0 < row.ttl <= 1800
            print(json.dumps({"at": datetime.now(UTC).isoformat(), "mode": args.mode, "key": key, "consistency": "ALL" if args.mode == "read-all" else "LOCAL_QUORUM", "write_coordinator": coordinator if args.mode == "write" else None, "read_coordinator": response.response_future.coordinator_host.address, "written_us": row.written_us, "ttl": row.ttl, "elapsed_ms": round((time.perf_counter() - start) * 1000, 2)}))
        else:
            print(json.dumps({"mode": args.mode, "key": key, "coordinator": coordinator, "removed": True}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
