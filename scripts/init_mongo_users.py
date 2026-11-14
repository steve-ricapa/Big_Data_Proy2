"""Idempotent local-only Mongo users. No password arguments, output or resets."""

from pathlib import Path

from pymongo import MongoClient

uri = Path("/run/secrets/mongodb_uri").read_text().strip()
with MongoClient(uri, serverSelectionTimeoutMS=8000) as client:
    db = client.threat_intelligence
    for user, role, file in (
        ("ti_pipeline", "readWrite", "mongodb_writer_password"),
        ("ti_reader", "read", "mongodb_reader_password"),
    ):
        current = db.command("usersInfo", user)["users"]
        if not current:
            password = Path("/run/secrets/" + file).read_text().strip()
            db.command("createUser", user, pwd=password, roles=[{"role": role, "db": db.name}])
        else:
            # Scope only these application users, never the admin or unrelated users.
            db.command("updateUser", user, roles=[{"role": role, "db": db.name}])
print("Local Mongo writer/read-only users configured; passwords not disclosed or reset.")
