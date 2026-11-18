from unittest.mock import Mock

import pytest
from cassandra import ConsistencyLevel
from cassandra.cluster import EXEC_PROFILE_DEFAULT

from threat_intelligence.common.config import Settings
from threat_intelligence.databases.cassandra import Cassandra


def test_quorum_client_discovers_peers_without_runtime_ddl(monkeypatch):
    driver = Mock()
    monkeypatch.setattr("threat_intelligence.databases.cassandra.Cluster", driver)
    with_settings = Settings(
        cassandra_contact_points="10.42.0.2, 10.42.0.12, 10.42.0.13",
        cassandra_consistency="LOCAL_QUORUM",
        cassandra_create_keyspace=False,
    )
    db = Cassandra(with_settings)
    assert driver.call_args.args[0] == ["10.42.0.2", "10.42.0.12", "10.42.0.13"]
    profile = driver.call_args.kwargs["execution_profiles"][EXEC_PROFILE_DEFAULT]
    assert profile.consistency_level == ConsistencyLevel.LOCAL_QUORUM
    assert profile.serial_consistency_level == ConsistencyLevel.LOCAL_SERIAL
    assert db.session.prepare.call_count == 7
    db.session.execute.assert_not_called()
    db.ping()
    assert "kpi_snapshots" in db.session.execute.call_args.args[0]
    db.close()
    driver.return_value.shutdown.assert_called_once()


def test_reject_unsafe_distributed_autocreate_and_empty_addresses():
    with pytest.raises(ValueError, match="pre-provisioned"):
        Cassandra(Settings(cassandra_consistency="LOCAL_QUORUM"))
    with pytest.raises(ValueError, match="contact points"):
        Cassandra(Settings(cassandra_contact_points="localhost,"))
