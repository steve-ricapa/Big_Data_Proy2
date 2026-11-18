"""Verify property and relationship CRUD with only UUID-scoped Neo4j probes."""

import json
import uuid

from threat_intelligence.pipeline import connect


def main():
    probe = str(uuid.uuid4())
    store = connect("neo4j")
    try:
        created = store.query("CREATE (a:TiAcceptanceProbe {probe:$p, role:'source'}), (b:TiAcceptanceProbe {probe:$p, role:'target'}), (a)-[r:TI_ACCEPTANCE_TEST {probe:$p, score:1}]->(b) RETURN r.score AS score", p=probe)
        assert created == [{"score": 1}]
        read = "MATCH (:TiAcceptanceProbe {probe:$p})-[r:TI_ACCEPTANCE_TEST {probe:$p}]->(:TiAcceptanceProbe {probe:$p}) "
        assert store.query(read + "RETURN r.score AS score", p=probe) == [{"score": 1}]
        assert store.query(read + "SET r.score=2 RETURN r.score AS score", p=probe) == [{"score": 2}]
        store.query(read + "DELETE r", p=probe)
        assert not store.query(read + "RETURN r.score AS score", p=probe)
    finally:
        try:
            store.query("MATCH (n:TiAcceptanceProbe {probe:$p}) DETACH DELETE n", p=probe)
            assert not store.query("MATCH (n:TiAcceptanceProbe {probe:$p}) RETURN n", p=probe)
        finally:
            store.close()
    print(json.dumps({"probe": probe, "relationship_crud": "PASS", "cleanup_verified": True}))


if __name__ == "__main__":
    main()
