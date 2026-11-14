"""NVD 2.0 bounded-window downloader; watermark advances only after ETL parity.

Pages are durable artifacts, never written into the original annual feeds.
One pipeline at a time, as required by the shared ETL checkpoints.
"""

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from threat_intelligence.common.io import write_json

URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def timestamp(value):
    return datetime.fromisoformat(value).astimezone(UTC)


def fetch(run_dir, state_dir, *, start=None, end=None, client=None, sleep=time.sleep):
    directory = Path(run_dir) / "nvd_sync"
    directory.mkdir(parents=True, exist_ok=True)
    journal = directory / "download.json"
    watermark = Path(state_dir) / "nvd_sync.json"
    if journal.exists():
        metadata = json.loads(journal.read_text(encoding="utf-8"))
    else:
        until = end or datetime.now(UTC) - timedelta(minutes=5)
        previous = json.loads(watermark.read_text()) if watermark.exists() else {}
        since = start
        if since is None:
            since = timestamp(previous["through"]) - timedelta(hours=2) if previous else until - timedelta(days=2)
        if since >= until:
            raise ValueError("NVD sync start must precede end")
        metadata = {"from": since.isoformat(), "through": until.isoformat(), "pages": [], "records": 0, "requests": 0, "retries": 0, "complete": False}
        write_json(journal, metadata)
    if metadata["complete"]:
        return metadata
    # API key is optional. Keep the public rate even with a key: <=5 calls/30s.
    headers = {"apiKey": os.environ["NVD_API_KEY"]} if os.getenv("NVD_API_KEY") else {}
    owned = client is None
    client = client or httpx.Client(timeout=90, follow_redirects=False, headers=headers)
    try:
        window_start = timestamp(metadata["from"])
        through = timestamp(metadata["through"])
        window_number = 0
        while window_start < through:
            window_end = min(window_start + timedelta(days=119), through)
            index = 0
            while True:
                filename = f"window-{window_number:05d}-page-{index:08d}.json"
                page_path = directory / filename
                if filename in metadata["pages"]:
                    payload = json.loads(page_path.read_text(encoding="utf-8"))
                else:
                    params = {"lastModStartDate": window_start.isoformat(timespec="milliseconds"), "lastModEndDate": window_end.isoformat(timespec="milliseconds"), "resultsPerPage": 2000, "startIndex": index}
                    for attempt in range(6):
                        sleep(6.2)
                        metadata["requests"] += 1
                        try:
                            response = client.get(URL, params=params)
                        except (httpx.TimeoutException, httpx.NetworkError):
                            response = None
                        if response is not None and response.status_code not in (429, 500, 502, 503, 504):
                            response.raise_for_status()
                            break
                        metadata["retries"] += 1
                        write_json(journal, metadata)
                        if attempt == 5:
                            raise RuntimeError("NVD unavailable after bounded retries")
                        retry_after = response.headers.get("Retry-After", "") if response is not None else ""
                        sleep(max(2 ** (attempt + 1), min(float(retry_after), 600) if retry_after.isdigit() else 0))
                    payload = response.json()
                    entries = payload.get("vulnerabilities")
                    if not isinstance(entries, list) or payload.get("startIndex") != index or not isinstance(payload.get("totalResults"), int):
                        raise ValueError("Invalid NVD pagination response")
                    if not entries and index < payload["totalResults"]:
                        raise ValueError("NVD returned a premature empty page")
                    write_json(page_path, payload)
                    metadata["pages"].append(filename)
                    metadata["records"] += len(entries)
                    write_json(journal, metadata)
                index += len(payload["vulnerabilities"])
                if index >= payload["totalResults"]:
                    break
            window_start = window_end
            window_number += 1
        metadata["complete"] = True
        write_json(journal, metadata)
        return metadata
    finally:
        if owned:
            client.close()


def prepare_sync(run_dir, state_dir, **kwargs):
    from threat_intelligence.pipeline import prepare, record_stage

    metadata = fetch(run_dir, state_dir, **kwargs)
    sources = [Path(run_dir) / "nvd_sync" / name for name in metadata["pages"]]
    path = prepare(run_dir, 0, sources)
    record_stage(path, "nvd_sync", metadata)
    return path


def commit_sync(run_dir, state_dir):
    from threat_intelligence.pipeline import manifest

    run = manifest(run_dir)
    sync = run["stages"].get("nvd_sync")
    if not sync:
        return
    if not sync["complete"] or "verify" not in run["stages"]:
        raise ValueError("Cannot advance NVD watermark before completed download and parity")
    for engine in ("mongodb", "cassandra", "neo4j"):
        if engine not in run["stages"] or run["stages"][engine].get("status") == "FAILED":
            raise ValueError("Cannot advance NVD watermark after partial ETL")
    if run["stages"]["validate"]["invalid"]:
        raise ValueError("Quarantined NVD records need review before watermark advancement")
    state = Path(state_dir) / "nvd_sync.json"
    previous = json.loads(state.read_text()) if state.exists() else {}
    if not previous or timestamp(sync["through"]) > timestamp(previous["through"]):
        write_json(state, {"through": sync["through"], "last_run": str(run_dir), "records": sync["records"], "committed_at": datetime.now(UTC).isoformat()})
