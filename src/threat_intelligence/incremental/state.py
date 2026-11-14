import json
import sqlite3
from pathlib import Path


class State:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=60)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints (sink TEXT, id TEXT, hash TEXT, modified TEXT, projection TEXT, PRIMARY KEY(sink,id))"
        )

    def previous(self, sink, row):
        return self.db.execute(
            "SELECT hash,modified,projection FROM checkpoints WHERE sink=? AND id=?",
            (sink, row["cve_id"]),
        ).fetchone()

    def changed(self, sink, row, force=False):
        old = self.previous(sink, row)
        if old and old[1] > row["last_modified"]:
            return False, old
        return force or not old or old[0] != row["content_hash"], old

    def commit(self, sink, rows):
        # Small analytical projection is sufficient to delete stale Cassandra keys.
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?,?)",
                [
                    (
                        sink,
                        r["cve_id"],
                        r["content_hash"],
                        r["last_modified"],
                        json.dumps(
                            {
                                k: r[k]
                                for k in (
                                    "cve_id",
                                    "month",
                                    "published",
                                    "severity",
                                    "cwes",
                                    "products",
                                )
                            }
                        ),
                    )
                    for r in rows
                ],
            )

    def close(self):
        self.db.close()
