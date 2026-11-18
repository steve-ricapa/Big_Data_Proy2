import re

from cassandra import ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import EXEC_PROFILE_DEFAULT, Cluster, ExecutionProfile
from cassandra.concurrent import execute_concurrent
from cassandra.policies import (
    DCAwareRoundRobinPolicy,
    ExponentialReconnectionPolicy,
    TokenAwarePolicy,
)


class Cassandra:
    def __init__(self, config, initialize_schema=True):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", config.cassandra_keyspace):
            raise ValueError("Invalid Cassandra keyspace")
        if not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,47}", config.cassandra_local_datacenter
        ):
            raise ValueError("Invalid Cassandra datacenter")
        auth = (
            PlainTextAuthProvider(config.cassandra_username, config.cassandra_password)
            if config.cassandra_username
            else None
        )
        contact_points = [host.strip() for host in config.cassandra_contact_points.split(",")]
        if not all(contact_points) or len(set(contact_points)) != len(contact_points):
            raise ValueError("Invalid Cassandra contact points")
        if config.cassandra_consistency not in {"LOCAL_ONE", "LOCAL_QUORUM"}:
            raise ValueError("Unsupported Cassandra consistency")
        if config.cassandra_consistency == "LOCAL_QUORUM" and config.cassandra_create_keyspace:
            raise ValueError("Distributed Cassandra requires a pre-provisioned keyspace")
        self.cluster = Cluster(
            contact_points,
            port=config.cassandra_port,
            auth_provider=auth,
            execution_profiles={EXEC_PROFILE_DEFAULT: ExecutionProfile(
                load_balancing_policy=TokenAwarePolicy(
                    DCAwareRoundRobinPolicy(local_dc=config.cassandra_local_datacenter)
                ),
                consistency_level=getattr(ConsistencyLevel, config.cassandra_consistency),
                serial_consistency_level=ConsistencyLevel.LOCAL_SERIAL,
                request_timeout=60,
            )},
            reconnection_policy=ExponentialReconnectionPolicy(1.0, 60.0, max_attempts=None),
            connect_timeout=15,
        )
        self.keyspace = config.cassandra_keyspace
        try:
            self.session = self.cluster.connect()
            self.session.default_fetch_size = 1000
            if initialize_schema and config.cassandra_create_keyspace:
                self.session.execute(
                    f"CREATE KEYSPACE IF NOT EXISTS {self.keyspace} WITH replication = {{'class':'NetworkTopologyStrategy','{config.cassandra_local_datacenter}':1}}"
                )
            self.session.set_keyspace(self.keyspace)
            if initialize_schema:
                self.initialize(manage_schema=config.cassandra_consistency != "LOCAL_QUORUM")
        except Exception:
            self.cluster.shutdown()
            raise

    def initialize(self, manage_schema=True):
        if manage_schema:
            self.create_tables()
        self.prepare_writes()

    def create_tables(self):
        self.session.execute(
            "CREATE TABLE IF NOT EXISTS cves_by_id (cve_id text PRIMARY KEY, content_hash text, document text)"
        )
        for table in ("cves_by_severity", "cves_by_product", "cves_by_cwe"):
            self.session.execute(
                f"CREATE TABLE IF NOT EXISTS {table} (bucket text, month text, published text, cve_id text, severity text, score double, description text, PRIMARY KEY ((bucket,month),published,cve_id)) WITH CLUSTERING ORDER BY (published DESC,cve_id ASC)"
            )
        self.session.execute(
            "CREATE TABLE IF NOT EXISTS kpi_snapshots (snapshot_id text PRIMARY KEY, payload text)"
        )
    def prepare_writes(self):
        self.insert_id = self.session.prepare(
            "INSERT INTO cves_by_id (cve_id,content_hash,document) VALUES (?,?,?)"
        )
        self.inserts = {
            t: self.session.prepare(
                f"INSERT INTO {t} (bucket,month,published,cve_id,severity,score,description) VALUES (?,?,?,?,?,?,?)"
            )
            for t in ("cves_by_severity", "cves_by_product", "cves_by_cwe")
        }
        self.deletes = {
            t: self.session.prepare(
                f"DELETE FROM {t} WHERE bucket=? AND month=? AND published=? AND cve_id=?"
            )
            for t in self.inserts
        }

    @staticmethod
    def keys(row):
        base = (row["month"], row["published"], row["cve_id"])
        return {
            ("cves_by_severity", row["severity"], *base),
            *(("cves_by_product", p["id"], *base) for p in row["products"]),
            *(("cves_by_cwe", cwe, *base) for cwe in row["cwes"]),
        }

    def write(self, rows, old=None):
        import json

        operations = []
        for row in rows:
            keys = self.keys(row)
            previous = (old or {}).get(row["cve_id"])
            if previous:
                for table, *key in self.keys(previous) - keys:
                    operations.append((self.deletes[table], tuple(key)))
            projection = {k: v for k, v in row.items() if k != "raw_cve"}
            operations.append(
                (
                    self.insert_id,
                    (row["cve_id"], row["content_hash"], json.dumps(projection)),
                )
            )
            for table, bucket, month, published, cve_id in keys:
                operations.append(
                    (
                        self.inserts[table],
                        (
                            bucket,
                            month,
                            published,
                            cve_id,
                            row["severity"],
                            row["cvss"]["score"] if row["cvss"] else None,
                            row["description"][:500],
                        ),
                    )
                )
        # Never advance a checkpoint after a partial failure. Replayed upserts/deletes are safe.
        for ok, value in execute_concurrent(
            self.session, operations, concurrency=16, raise_on_first_error=False
        ):
            if not ok:
                raise value

    def ping(self):
        self.session.execute("SELECT snapshot_id FROM kpi_snapshots WHERE snapshot_id = 'latest'")

    def count(self):
        # A larger client timeout cannot prevent coordinator COUNT(*) timeouts.
        from cassandra.query import SimpleStatement

        return sum(
            1
            for _ in self.session.execute(
                SimpleStatement("SELECT cve_id FROM cves_by_id", fetch_size=1000)
            )
        )

    def close(self):
        self.cluster.shutdown()
