"""Opt-in real-engine tests: no mock adapters and no public database ports."""

import os

import pytest

from threat_intelligence.crud import run_crud
from threat_intelligence.pipeline import connect

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("TI_INTEGRATION") != "1",
        reason="Set TI_INTEGRATION=1 inside Docker private network",
    ),
]


@pytest.mark.parametrize("engine", ["mongodb", "cassandra", "neo4j"])
def test_actual_engine_crud(engine):
    result = run_crud((engine,))
    assert set(result["engines"][engine].values()) == {"PASS"}


@pytest.mark.parametrize("engine", ["mongodb", "cassandra", "neo4j"])
def test_actual_engine_readiness_and_nonempty(engine):
    sink = connect(engine)
    try:
        sink.ping()
        assert sink.count() >= 1000
    finally:
        sink.close()


def test_api_mongodb_identity_cannot_write():
    from pathlib import Path
    from uuid import uuid4

    from pymongo import MongoClient
    from pymongo.errors import OperationFailure

    reader_uri = Path("/run/secrets/mongodb_reader_uri").read_text().strip()
    identifier = "permission-test-" + uuid4().hex
    writer = connect("mongodb")
    try:
        with MongoClient(reader_uri, serverSelectionTimeoutMS=8000) as client:
            assert client.threat_intelligence.cves.find_one({}, {"cve_id": 1})
            with pytest.raises(OperationFailure) as error:
                client.threat_intelligence.permission_probe.insert_one({"_id": identifier})
            assert error.value.code == 13
    finally:
        writer.db.permission_probe.delete_one({"_id": identifier})
        writer.close()


@pytest.mark.skipif(os.getenv("TI_SECURE_TESTS") != "1", reason="requires Cassandra security overlay")
def test_cassandra_reader_cannot_write():
    from pathlib import Path

    from cassandra import Unauthorized

    from threat_intelligence.common.config import settings
    from threat_intelligence.databases.cassandra import Cassandra

    password = Path("/run/secrets/cassandra_reader_password").read_text().strip()
    config = settings().model_copy(update={"cassandra_username": "ti_reader", "cassandra_password": password})
    store = Cassandra(config, initialize_schema=False)
    try:
        session = store.session
        assert session.execute("SELECT cve_id FROM cves_by_id LIMIT 1").one()
        with pytest.raises(Unauthorized):
            session.execute("DELETE FROM cves_by_id WHERE cve_id=%s", ("CVE-2099-0000000000000000001",))
    finally:
        store.close()
