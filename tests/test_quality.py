import copy
import json

from threat_intelligence.analytics.kpis import calculate
from threat_intelligence.common.io import ndjson
from threat_intelligence.pipeline import prepare, validate
from threat_intelligence.transformations.normalize import normalize


def test_equal_timestamp_dedup_order_independent(cve, tmp_path):
    modified = copy.deepcopy(cve)
    modified["descriptions"][0]["value"] = "Other content, same timestamp"
    expected_hash = max(
        normalize(cve)["content_hash"], normalize(modified)["content_hash"]
    )
    for index, entries in enumerate(([cve, modified], [modified, cve])):
        source = tmp_path / f"{index}.json"
        source.write_text(
            json.dumps({"vulnerabilities": [{"cve": row} for row in entries]})
        )
        run = tmp_path / f"run{index}"
        prepare(run, sources=[source])
        assert validate(run)["duplicates"] == 1
        assert next(ndjson(run / "canonical.ndjson"))["content_hash"] == expected_hash


def test_rejected_population_explicit(cve):
    cve["vulnStatus"] = "Rejected"
    result = calculate([normalize(cve)])
    assert result["total_cves"] == 1
    assert result["rejected_cves"] == 1


def test_vendor_counts_unique_cve_not_product(cve):
    match = cve["configurations"][0]["nodes"][0]["cpeMatch"][0]
    cve["configurations"][0]["nodes"][0]["cpeMatch"].append(
        {**match, "criteria": match["criteria"].replace(":product:", ":product2:")}
    )
    result = calculate([normalize(cve)])
    assert result["unique_affected_products"] == 2
    assert result["top_vendors"] == [("vendor", 1)]


def test_cvss_secondary_does_not_override_primary(cve):
    cve["metrics"]["cvssMetricV31"].insert(
        0,
        {
            "type": "Secondary",
            "source": "aaa",
            "cvssData": {"version": "3.1", "baseScore": 1.0},
        },
    )
    assert normalize(cve)["cvss"]["score"] == 9.8


def test_cassandra_count_pages_instead_of_coordinator_aggregate():
    from threat_intelligence.databases.cassandra import Cassandra

    class Session:
        def execute(self, statement):
            assert statement.fetch_size == 1000
            assert statement.query_string == "SELECT cve_id FROM cves_by_id"
            return iter([("CVE-2024-1000",), ("CVE-2024-1001",)])

    sink = object.__new__(Cassandra)
    sink.session = Session()
    assert sink.count() == 2
