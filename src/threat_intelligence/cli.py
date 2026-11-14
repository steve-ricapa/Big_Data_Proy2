import argparse
import json

from threat_intelligence.common.config import settings
from threat_intelligence.common.io import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "inventory",
            "prepare",
            "validate",
            "mongodb",
            "cassandra",
            "neo4j",
            "kpis",
            "verify",
            "run",
            "crud",
            "selftest",
            "audit-kpis",
            "sync",
        ],
    )
    parser.add_argument("--run-dir", default="data/staging/demo")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--source", action="append")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output", default="docs/evidence/inventory.json")
    args = parser.parse_args()
    if args.command == "audit-kpis":
        from threat_intelligence.analytics.audit import audit_kpis

        write_json(args.output, audit_kpis())
        return
    if args.command == "selftest":
        from threat_intelligence.selftest import run_selftest

        write_json(args.output, run_selftest())
        return
    if args.command == "inventory":
        from threat_intelligence.ingestion.nvd import inventory

        result = inventory(settings().nvd_raw_dir)
        write_json(args.output, result)
        print(
            json.dumps(
                {
                    "entries": sum(r["count"] for r in result),
                    "files": len(result),
                    "evidence": args.output,
                }
            )
        )
        return
    if args.command == "crud":
        from threat_intelligence.crud import run_crud

        write_json(args.output, run_crud())
        return
    from threat_intelligence import pipeline

    command = args.command
    if command == "sync":
        from threat_intelligence.ingestion.sync import commit_sync, prepare_sync

        prepare_sync(args.run_dir, settings().state_dir)
        pipeline.validate(args.run_dir)
        for engine in ("mongodb", "cassandra", "neo4j"):
            pipeline.load(args.run_dir, engine)
        pipeline.kpis(args.run_dir)
        pipeline.verify(args.run_dir)
        commit_sync(args.run_dir, settings().state_dir)
        return
    if command in ("prepare", "run"):
        pipeline.prepare(args.run_dir, args.limit, args.source)
    if command in ("validate", "run"):
        pipeline.validate(args.run_dir)
    for engine in ("mongodb", "cassandra", "neo4j"):
        if command in (engine, "run"):
            pipeline.load(args.run_dir, engine, args.force)
    if command in ("kpis", "run"):
        pipeline.kpis(args.run_dir)
    if command in ("verify", "run"):
        pipeline.verify(args.run_dir)


if __name__ == "__main__":
    main()
