"""Apply RF=3 only on the known, fully joined ring (run on primary host)."""

import json
from pathlib import Path

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster

HOSTS = {"10.42.0.2": "rack1", "10.42.0.12": "us-central1-b", "10.42.0.13": "us-central1-c"}
KEYSPACES = ("threat_intelligence", "system_auth")


def main():
    auth = PlainTextAuthProvider("ti_admin", Path("/run/secrets/admin").read_text().strip())
    with Cluster(list(HOSTS), auth_provider=auth, connect_timeout=10) as cluster, cluster.connect() as session:
        session.default_timeout = 60
        coordinator = next(h for h in cluster.metadata.all_hosts() if h.address == "10.42.0.2")
        local = session.execute("SELECT cluster_name,broadcast_address,data_center,rack FROM system.local", host=coordinator).one()
        peers = session.execute("SELECT peer,data_center,rack FROM system.peers_v2", host=coordinator)
        observed = {str(local.broadcast_address): local.rack}
        for peer in peers:
            assert peer.data_center == "dc1"
            observed[str(peer.peer)] = peer.rack
        assert observed == HOSTS and local.cluster_name == "ti-dev-single-node" and local.data_center == "dc1", (observed, local)
        assert len(cluster.metadata.all_hosts()) == 3 and all(h.is_up for h in cluster.metadata.all_hosts())
        before = {name: cluster.metadata.keyspaces[name].replication_strategy.export_for_schema() for name in KEYSPACES}
        for name in KEYSPACES:
            session.execute(f"ALTER KEYSPACE {name} WITH replication = {{'class':'NetworkTopologyStrategy','dc1':3}} AND durable_writes=true")
        assert cluster.control_connection.wait_for_schema_agreement()
        after = {row.keyspace_name: dict(row.replication) for row in session.execute("SELECT keyspace_name,replication FROM system_schema.keyspaces") if row.keyspace_name in KEYSPACES}
        assert all(after[name]["dc1"] == "3" for name in KEYSPACES)
        print(json.dumps({"hosts": observed, "before": before, "after": after}))


if __name__ == "__main__":
    main()
