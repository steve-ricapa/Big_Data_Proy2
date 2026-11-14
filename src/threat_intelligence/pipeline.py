import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from threat_intelligence.common.config import settings
from threat_intelligence.common.io import batches, ndjson, write_json
from threat_intelligence.incremental.state import State
from threat_intelligence.ingestion.nvd import records
from threat_intelligence.transformations.normalize import normalize


def prepare(run_dir, limit=0, sources=None):
    config = settings()
    paths = (
        [Path(p) for p in sources]
        if sources
        else sorted(config.nvd_raw_dir.rglob("nvdcve-2.0-*.json"))
    )
    if not paths:
        raise FileNotFoundError("No NVD sources")
    if limit < 0:
        raise ValueError("limit must be >= 0")
    manifest = {
        "run_dir": str(Path(run_dir).resolve()),
        "sources": [str(p.resolve()) for p in paths],
        "limit": limit,
        "started_at": datetime.now(UTC).isoformat(),
        "stages": {},
    }
    write_json(Path(run_dir) / "run.json", manifest)
    return str(Path(run_dir).resolve())


def manifest(run_dir):
    return json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8"))


def record_stage(run_dir, name, data):
    value = manifest(run_dir)
    value["stages"][name] = data
    write_json(Path(run_dir) / "run.json", value)
    print(json.dumps({"stage": name, **data}), flush=True)
    return data


def validate(run_dir):
    config = manifest(run_dir)
    path = Path(run_dir)
    # Random SQLite I/O on a Windows bind mount is prohibitively slow.
    # Work on container-local disk, then publish the reproducible artifact.
    descriptor, temporary_db = tempfile.mkstemp(
        prefix="nvd-canonical-", suffix=".sqlite"
    )
    os.close(descriptor)
    db = sqlite3.connect(temporary_db)
    db.execute(
        "CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, modified TEXT, hash TEXT, document TEXT)"
    )
    db.execute("DELETE FROM records")
    stats = {"seen": 0, "invalid": 0, "duplicates": 0}
    with (path / "quarantine.ndjson").open("w", encoding="utf-8") as rejected:
        for source in config["sources"]:
            for entry in records(Path(source)):
                if config["limit"] and stats["seen"] >= config["limit"]:
                    break
                stats["seen"] += 1
                try:
                    row = normalize(entry)
                except (ValueError, KeyError, TypeError, AttributeError) as error:
                    stats["invalid"] += 1
                    rejected.write(
                        json.dumps(
                            {
                                "reason": type(error).__name__ + ":" + str(error),
                                "source": source,
                                "record": entry,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    continue
                db.execute(
                    "INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET modified=excluded.modified,hash=excluded.hash,document=excluded.document WHERE excluded.modified>records.modified OR (excluded.modified=records.modified AND excluded.hash>records.hash)",
                    (
                        row["cve_id"],
                        row["last_modified"],
                        row["content_hash"],
                        json.dumps(row, ensure_ascii=False),
                    ),
                )
                if stats["seen"] % 1000 == 0:
                    db.commit()
                if stats["seen"] % 10000 == 0:
                    print(
                        json.dumps(
                            {"stage": "validate_progress", "seen": stats["seen"]}
                        ),
                        flush=True,
                    )
        db.commit()
    temp = path / "canonical.ndjson.tmp"
    with temp.open("w", encoding="utf-8") as stream:
        for (document,) in db.execute("SELECT document FROM records ORDER BY id"):
            stream.write(document + "\n")
    temp.replace(path / "canonical.ndjson")
    stats["unique_valid"] = db.execute("SELECT count(*) FROM records").fetchone()[0]
    stats["duplicates"] = stats["seen"] - stats["invalid"] - stats["unique_valid"]
    db.close()
    shutil.copyfile(temporary_db, path / "canonical.sqlite.tmp")
    (path / "canonical.sqlite.tmp").replace(path / "canonical.sqlite")
    Path(temporary_db).unlink()
    if not stats["unique_valid"] and not config["stages"].get("nvd_sync", {}).get("complete"):
        raise ValueError("No valid CVEs; refusing an empty successful load")
    return record_stage(run_dir, "validate", stats)


def connect(name):
    config = settings()
    if name == "mongodb":
        from threat_intelligence.databases.mongodb import Mongo

        return Mongo(config)
    if name == "cassandra":
        from threat_intelligence.databases.cassandra import Cassandra

        return Cassandra(config)
    if name == "neo4j":
        from threat_intelligence.databases.neo4j import Neo

        return Neo(config)
    raise ValueError("Unknown engine")


def load(run_dir, engine, force=False):
    started = time.monotonic()
    sink = state = None
    stats = {
        "seen": 0,
        "new": 0,
        "modified": 0,
        "unchanged": 0,
        "stale": 0,
        "written": 0,
        "batches_committed": 0,
    }
    try:
        sink = connect(engine)
        state = State(settings().state_dir / "checkpoints.sqlite")
        sink.initialize()
        sink.ping()
        force = force or sink.count() == 0
        for batch in batches(
            ndjson(Path(run_dir) / "canonical.ndjson"), settings().batch_size
        ):
            changed, old_rows = [], {}
            for row in batch:
                stats["seen"] += 1
                dirty, old = state.changed(engine, row, force)
                if not dirty:
                    stats[
                        "stale"
                        if old and old[1] > row["last_modified"]
                        else "unchanged"
                    ] += 1
                    continue
                changed.append(row)
                stats["new" if old is None else "modified"] += 1
                if old:
                    old_rows[row["cve_id"]] = json.loads(old[2])
            if changed:
                sink.write(changed, old_rows)
                state.commit(engine, changed)
                stats["written"] += len(changed)
                stats["batches_committed"] += 1
            if stats["seen"] % 10000 == 0:
                print(json.dumps({"stage": engine + "_progress", **stats}), flush=True)
        stats["total_in_engine"] = sink.count()
        stats["seconds"] = round(time.monotonic() - started, 3)
        return record_stage(run_dir, engine, stats)
    except Exception as error:
        record_stage(
            run_dir,
            engine,
            {**stats, "status": "FAILED", "error_type": type(error).__name__},
        )
        raise
    finally:
        if sink is not None:
            sink.close()
        if state is not None:
            state.close()


def kpis(run_dir):
    from threat_intelligence.analytics.kpis import calculate

    mongo = connect("mongodb")
    try:
        result = calculate(
            mongo.collection.find({}, {"raw_cve": 0, "_id": 0}).batch_size(200)
        )
        graph = connect("neo4j")
        try:
            result["graph"] = {
                "nodes": graph.query("MATCH (n) RETURN count(n) AS n")[0]["n"],
                "relationships": graph.query("MATCH ()-[r]->() RETURN count(r) AS n")[
                    0
                ]["n"],
            }
        finally:
            graph.close()
        mongo.db.kpis.replace_one(
            {"_id": "latest"}, {"_id": "latest", **result}, upsert=True
        )
        cassandra = connect("cassandra")
        try:
            cassandra.session.execute(
                cassandra.session.prepare(
                    "INSERT INTO kpi_snapshots (snapshot_id,payload) VALUES (?,?)"
                ),
                ("latest", json.dumps(result)),
            )
        finally:
            cassandra.close()
        write_json(Path(run_dir) / "kpis.json", result)
        return record_stage(
            run_dir,
            "kpis",
            {"total_cves": result["total_cves"], "as_of": result["as_of"]},
        )
    finally:
        mongo.close()


def verify(run_dir):
    counts = {}
    fingerprints = {}
    for engine in ("mongodb", "cassandra", "neo4j"):
        sink = connect(engine)
        try:
            counts[engine] = sink.count()

            # Order-independent SHA-256 multiset fingerprint over every identity/hash.
            # Unlike counts alone, this detects different CVEs or stale content.
            def fingerprint(rows):
                total = n = 0
                for identifier, content_hash in rows:
                    total = (
                        total
                        + int.from_bytes(
                            hashlib.sha256(
                                (identifier + ":" + content_hash).encode()
                            ).digest(),
                            "big",
                        )
                    ) % (1 << 256)
                    n += 1
                return {"records": n, "sha256_sum": f"{total:064x}"}

            if engine == "mongodb":
                fingerprints[engine] = fingerprint(
                    (r["cve_id"], r["content_hash"])
                    for r in sink.collection.find(
                        {}, {"cve_id": 1, "content_hash": 1, "_id": 0}
                    ).batch_size(500)
                )
            elif engine == "cassandra":
                fingerprints[engine] = fingerprint(
                    (r.cve_id, r.content_hash)
                    for r in sink.session.execute(
                        "SELECT cve_id,content_hash FROM cves_by_id"
                    )
                )
            else:
                with sink.driver.session(database=sink.database) as session:
                    fingerprints[engine] = fingerprint(
                        (r["id"], r["hash"])
                        for r in session.run(
                            "MATCH (c:CVE) RETURN c.id AS id,c.content_hash AS hash"
                        )
                    )
        finally:
            sink.close()
    if len(set(counts.values())) != 1:
        raise ValueError(f"Engine count mismatch: {counts}")
    if len({json.dumps(v, sort_keys=True) for v in fingerprints.values()}) != 1:
        raise ValueError(f"Engine identity/content mismatch: {fingerprints}")
    record_stage(run_dir, "verify", {"counts": counts, "fingerprints": fingerprints})
    mongo = connect("mongodb")
    try:
        mongo.db.pipeline_runs.replace_one(
            {"_id": str(Path(run_dir).resolve())},
            {
                "_id": str(Path(run_dir).resolve()),
                **manifest(run_dir),
                "status": "SUCCESS",
            },
            upsert=True,
        )
    finally:
        mongo.close()
    return counts
