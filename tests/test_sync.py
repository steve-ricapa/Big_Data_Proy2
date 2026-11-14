import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from threat_intelligence.ingestion.sync import commit_sync, fetch, prepare_sync
from threat_intelligence.pipeline import record_stage, validate

START = datetime(2026, 1, 1, tzinfo=UTC)


def test_pagination_rate_limit_and_resume(tmp_path):
    calls, waits = [], []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "10"})
        index = int(request.url.params["startIndex"])
        return httpx.Response(200, json={"startIndex": index, "totalResults": 2, "vulnerabilities": [{"cve": {"id": str(index)}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch(tmp_path / "run", tmp_path / "state", start=START, end=START + timedelta(days=1), client=client, sleep=waits.append)
        assert result["records"] == 2 and result["retries"] == 1 and len(result["pages"]) == 2
        assert waits.count(6.2) == 3 and 10 in waits
        assert fetch(tmp_path / "run", tmp_path / "state", client=client) == result
        assert len(calls) == 3
    assert not (tmp_path / "state/nvd_sync.json").exists()


def test_partial_download_recovers_without_watermark(tmp_path):
    def handler(request):
        index = int(request.url.params["startIndex"])
        if index:
            return httpx.Response(503)
        return httpx.Response(200, json={"startIndex": 0, "totalResults": 2, "vulnerabilities": [{}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(RuntimeError, match="bounded retries"):
        fetch(tmp_path / "run", tmp_path / "state", start=START, end=START + timedelta(days=1), client=client, sleep=lambda _: None)
    journal = json.loads((tmp_path / "run/nvd_sync/download.json").read_text())
    assert len(journal["pages"]) == 1 and not journal["complete"]
    assert not (tmp_path / "state/nvd_sync.json").exists()


def test_empty_sync_is_valid_and_only_commits_after_parity(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"startIndex": 0, "totalResults": 0, "vulnerabilities": []}))) as client:
        run = prepare_sync(tmp_path / "run", tmp_path / "state", start=START, end=START + timedelta(days=1), client=client, sleep=lambda _: None)
    assert validate(run)["unique_valid"] == 0
    with pytest.raises(ValueError, match="parity"):
        commit_sync(run, tmp_path / "state")
    for stage in ("mongodb", "cassandra", "neo4j", "verify"):
        record_stage(run, stage, {})
    commit_sync(run, tmp_path / "state")
    assert json.loads((tmp_path / "state/nvd_sync.json").read_text())["through"] == (START + timedelta(days=1)).isoformat()


def test_windows_are_bounded_and_overlap_watermark(tmp_path):
    windows = []

    def handler(request):
        windows.append(request.url.params)
        return httpx.Response(200, json={"startIndex": 0, "totalResults": 0, "vulnerabilities": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetch(tmp_path / "run", tmp_path / "state", start=START, end=START + timedelta(days=240), client=client, sleep=lambda _: None)
    assert len(windows) == 3
    for window in windows:
        assert datetime.fromisoformat(window["lastModEndDate"]) - datetime.fromisoformat(window["lastModStartDate"]) <= timedelta(days=119)
