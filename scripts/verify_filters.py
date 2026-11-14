"""Real Explorer filter checks and timing; no DB writes or invented latency."""

import argparse
import json
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="docs/evidence/filter_validation.json")
args = parser.parse_args()
results = []
with httpx.Client(base_url="http://127.0.0.1:18000", timeout=30) as client:
    for filters in (
        {"year": 2024},
        {"severity": "CRITICAL"},
        {"cwe": "CWE-79"},
        {"published_from": "2024-01-01", "published_to": "2024-12-31"},
    ):
        start = time.monotonic()
        response = client.get("/api/v1/vulnerabilities", params={"page_size": 2, **filters})
        response.raise_for_status()
        data = response.json()
        assert data["items"] and len(data["items"]) <= 2
        for row in data["items"]:
            if "year" in filters:
                assert row["year"] == filters["year"]
            if "severity" in filters:
                assert row["severity"] == filters["severity"]
            if "cwe" in filters:
                assert filters["cwe"] in row["cwes"]
            if "published_from" in filters:
                assert filters["published_from"] <= row["published"][:10] <= filters["published_to"]
        results.append({"filters": filters, "status": response.status_code, "seconds": round(time.monotonic() - start, 3), "total": data["total"], "checks": "PASS"})
Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results))
