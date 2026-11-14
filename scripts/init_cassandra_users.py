"""Bootstrap Cassandra auth on isolated network; never logs CQL/passwords."""

import os
import time
from pathlib import Path

from cassandra import AuthenticationFailed
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, NoHostAvailable


def connect(username, password):
    cluster = Cluster(["cassandra"], auth_provider=PlainTextAuthProvider(username, password))
    try:
        return cluster, cluster.connect()
    except (NoHostAvailable, AuthenticationFailed):
        cluster.shutdown()
        raise


def password(name):
    return Path("/run/secrets/" + name).read_text().strip().replace("'", "''")


def main():
    admin = password("cassandra_admin_password")
    for attempt in range(30):
        try:
            cluster, session = connect("ti_admin", admin)
            break
        except (NoHostAvailable, AuthenticationFailed):
            if os.getenv("TI_ALLOW_DEFAULT_CASSANDRA_BOOTSTRAP") == "1":
                try:
                    cluster, session = connect("cassandra", "cassandra")
                    session.execute(f"CREATE ROLE IF NOT EXISTS ti_admin WITH PASSWORD = '{admin}' AND LOGIN = true AND SUPERUSER = true")
                    cluster.shutdown()
                    cluster, session = connect("ti_admin", admin)
                    break
                except (NoHostAvailable, AuthenticationFailed):
                    pass
            if attempt == 29:
                raise RuntimeError("Cassandra authenticated bootstrap unavailable") from None
            time.sleep(5)
    try:
        session.execute("CREATE KEYSPACE IF NOT EXISTS threat_intelligence WITH replication = {'class':'NetworkTopologyStrategy','dc1':1}")
        for role, secret in (("ti_pipeline", "cassandra_writer_password"), ("ti_reader", "cassandra_reader_password")):
            session.execute(f"CREATE ROLE IF NOT EXISTS {role} WITH PASSWORD = '{password(secret)}' AND LOGIN = true AND SUPERUSER = false")
        for permission in ("SELECT", "MODIFY", "CREATE", "ALTER"):
            session.execute(f"GRANT {permission} ON KEYSPACE threat_intelligence TO ti_pipeline")
        session.execute("GRANT SELECT ON KEYSPACE threat_intelligence TO ti_reader")
        # No default credentials remain usable, including the superuser account.
        session.execute(f"ALTER ROLE cassandra WITH PASSWORD = '{admin}' AND LOGIN = false")
    finally:
        cluster.shutdown()
    print("Cassandra auth enabled; scoped writer/reader and nondefault admin configured.")


if __name__ == "__main__":
    main()
