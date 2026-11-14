import copy
import json
from datetime import UTC, datetime

import pytest

from threat_intelligence.analytics.kpis import calculate
from threat_intelligence.common.io import ndjson
from threat_intelligence.incremental.state import State
from threat_intelligence.ingestion.nvd import inventory, records
from threat_intelligence.pipeline import prepare, validate
from threat_intelligence.transformations.normalize import cpe_parts, date, normalize


def test_normalize(cve):
    row = normalize({"cve": cve})
    assert row["cve_id"] == cve["id"]
    assert row["severity"] == "CRITICAL"
    assert row["cwes"] == ["CWE-79"]
    assert len(row["products"]) == 1
    assert row["raw_cve"] == cve
    assert row["content_hash"] == normalize(cve)["content_hash"]


@pytest.mark.parametrize(
    "identifier", ["", "CVE-foo", "CVE-2024-1", "CVE-2024-1234;DROP"]
)
def test_invalid_id(cve, identifier):
    cve["id"] = identifier
    with pytest.raises(ValueError):
        normalize(cve)


@pytest.mark.parametrize(
    "value", [True, -1, 11, float("nan"), float("inf"), "9.8", None]
)
def test_invalid_score(cve, value):
    cve["metrics"]["cvssMetricV31"][0]["cvssData"]["baseScore"] = value
    assert normalize(cve)["cvss"] is None


def test_cvss_priority_and_no_mixing(cve):
    cve["metrics"]["cvssMetricV40"] = [
        {"cvssData": {"version": "4.0", "baseScore": 7.1}}
    ]
    first = normalize(cve)
    del cve["metrics"]["cvssMetricV40"]
    second = normalize(cve)
    data = calculate([first, second])
    assert data["cvss_by_version"] == {
        "4.0": {"count": 1, "average": 7.1},
        "3.1": {"count": 1, "average": 9.8},
    }


def test_unknown_not_zero(cve):
    cve["metrics"] = {}
    row = normalize(cve)
    assert row["severity"] == "UNKNOWN"
    assert calculate([row])["cvss_by_version"] == {}


def test_cpe_escape():
    assert cpe_parts(r"cpe:2.3:a:ven\:dor:prod:1:*:*:*:*:*:*:*")[3] == "ven:dor"
    assert cpe_parts("invalid") is None


def test_product_dedup(cve):
    match = cve["configurations"][0]["nodes"][0]["cpeMatch"][0]
    cve["configurations"][0]["nodes"][0]["cpeMatch"].append(
        {**match, "criteria": match["criteria"].replace(":1.0:", ":2.0:")}
    )
    row = normalize(cve)
    assert len(row["cpes"]) == 2
    assert len(row["products"]) == 1
    result = calculate([row])
    assert result["top_products"][0][1] == 1


def test_dates():
    assert date("2024-01-01T01:00:00+01:00") == date("2024-01-01T00:00:00Z")
    assert date("2024-01-01T00:00:00.100") < date("2024-01-01T00:00:01")


def test_checkpoint_independence_and_stale(cve, tmp_path):
    state = State(tmp_path / "state.sqlite")
    row = normalize(cve)
    assert state.changed("mongodb", row)[0]
    state.commit("mongodb", [row])
    assert not state.changed("mongodb", row)[0]
    assert state.changed("cassandra", row)[0]
    cve["lastModified"] = "2026-10-01T00:00:00Z"
    assert not state.changed("mongodb", normalize(cve), force=True)[0]
    state.close()
    state = State(tmp_path / "state.sqlite")
    assert not state.changed("mongodb", row)[0]
    state.close()


def test_modification(cve, tmp_path):
    state = State(tmp_path / "state.sqlite")
    state.commit("neo4j", [normalize(cve)])
    cve["descriptions"][0]["value"] = "Modified"
    assert state.changed("neo4j", normalize(cve))[0]
    state.close()


def test_stream_inventory_and_dedup(cve, tmp_path):
    newer = copy.deepcopy(cve)
    newer["lastModified"] = "2026-11-02T00:00:00Z"
    invalid = {"id": "invalid"}
    source = tmp_path / "nvdcve-2.0-test.json"
    source.write_text(
        json.dumps(
            {
                "totalResults": 3,
                "vulnerabilities": [{"cve": v} for v in [newer, cve, invalid]],
            }
        )
    )
    assert len(list(records(source))) == 3
    assert inventory(tmp_path)[0]["count"] == 3
    run = tmp_path / "run"
    prepare(run, sources=[source])
    stats = validate(run)
    assert stats == {"seen": 3, "invalid": 1, "duplicates": 1, "unique_valid": 1}
    assert next(ndjson(run / "canonical.ndjson"))["last_modified"] == date(
        newer["lastModified"]
    )
    assert len(list(ndjson(run / "quarantine.ndjson"))) == 1


def test_kpi_recent_window(cve):
    row = normalize(cve)
    result = calculate([row], datetime(2026, 11, 10, tzinfo=UTC))
    assert result["modified_last_30_days"] == 1
    assert result["total_cves"] == 1
    assert result["monthly"] == {"2024-01": 1}
    assert result["severity_percent"] == {"CRITICAL": 100}
    assert (
        calculate([row], datetime(2026, 10, 1, tzinfo=UTC))["modified_last_30_days"]
        == 0
    )


def test_empty_kpi():
    assert calculate([])["total_cves"] == 0


def test_empty_validation_refused(tmp_path):
    source = tmp_path / "empty.json"
    source.write_text('{"vulnerabilities": []}')
    prepare(tmp_path / "run", sources=[source])
    with pytest.raises(ValueError):
        validate(tmp_path / "run")
