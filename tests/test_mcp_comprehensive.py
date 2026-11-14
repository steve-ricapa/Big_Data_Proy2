import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from mcp.server.fastmcp.exceptions import ToolError

from services.api.app import app
from services.api.views import (
    ReadViews,
    applicability,
    enriched_cpes,
    summary_projection,
)
from services.mcp_server import server


def test_all_six_schemas_are_closed_typed_and_complete():
    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) == 6
    for tool in tools:
        assert tool.inputSchema["additionalProperties"] is False
        assert tool.outputSchema["type"] == "object"
        assert tool.outputSchema["properties"]
    search = next(t for t in tools if t.name == "search_vulnerabilities")
    assert {"keyword", "severity", "cve_id", "page", "page_size", "view", "fields"} <= search.inputSchema["properties"].keys()
    assert search.inputSchema["properties"]["page"]["anyOf"][0]["maximum"] == 10000
    assert search.inputSchema["properties"]["page_size"]["anyOf"][0]["maximum"] == 100
    products = next(t for t in tools if t.name == "get_affected_products")
    assert {"items", "cpes", "mode", "metadata"} <= products.outputSchema["properties"].keys()


@pytest.mark.parametrize("name,arguments", [
    ("search_vulnerabilities", {"unexpected_parameter": "never-echo-this-value"}),
    ("get_cve_details", {"cve_id": "CVE-2021-44228", "unexpected_parameter": "never-echo-this-value"}),
    ("get_affected_products", {"limit": 1}),
    ("explore_cve_relationships", {"cve_id": "CVE-2021-44228", "limit": 1}),
    ("get_top_cwes", {"limit": 1}),
    ("get_top_cwes", {"limit": "bad"}),
    ("get_vulnerability_statistics", {"unexpected_parameter": "never-echo-this-value"}),
])
def test_unknown_arguments_are_rejected_before_http(monkeypatch, name, arguments):
    def forbidden(*_args, **_kwargs):
        pytest.fail("An invalid MCP argument reached HTTP")

    monkeypatch.setattr(server, "query", forbidden)
    with pytest.raises(ToolError, match="extra_forbidden") as error:
        asyncio.run(server.mcp.call_tool(name, arguments))
    assert "never-echo-this-value" not in str(error.value)


@pytest.mark.parametrize("field,value", [("page", True), ("page", 2.0), ("page", "2.0"), ("page", 0), ("page_size", 101), ("page", "-1"), ("page", "10001"), ("page_size", "101"), ("fields", [])])
def test_page_validation_is_not_blind_coercion(field, value):
    with pytest.raises(ToolError, match="Invalid arguments"):
        asyncio.run(server.mcp.call_tool("search_vulnerabilities", {field: value}))


def test_digit_string_page_compatibility_and_structured_content(monkeypatch):
    def query(_path, **params):
        assert params["page"] == 2 and type(params["page"]) is int
        return {"items": [], "total": 0, "page": 2, "page_size": 25}

    monkeypatch.setattr(server, "query", query)
    result = asyncio.run(server.mcp.call_tool("search_vulnerabilities", {"page": "2"}))
    content, structured = result.content, result.structuredContent
    assert structured == {"items": [], "total": 0, "page": 2, "page_size": 25}
    assert json.loads(content[0].text) == structured


def test_mcp_boolean_strings_rejected():
    with pytest.raises(ToolError, match="Invalid arguments"):
        asyncio.run(server.mcp.call_tool("get_cve_details", {"cve_id": "CVE-2021-44228", "include_raw": "false"}))


def test_structured_output_preserves_legacy_additive_fields(monkeypatch):
    body = {"total_cves": 3, "as_of": "cut", "severity": {"HIGH": 3}, "rejected_cves": 0,
            "top_products": [["identity", 3]], "monthly": {"2026-11": 3}, "legacy_extension": {"retained": True}}
    monkeypatch.setattr(server, "query", lambda *args, **kwargs: body)
    result = asyncio.run(server.mcp.call_tool("get_vulnerability_statistics", {}))
    assert result.structuredContent == json.loads(result.content[0].text) == body


def test_applicability_keeps_every_occurrence_and_boolean_context():
    criteria = "cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*"
    raw = {"id": "CVE-2021-44228", "descriptions": [{"lang": "en", "value": "Description mentions 2.15.0"}], "configurations": [{
        "operator": "AND", "negate": False, "nodes": [{"operator": "OR", "cpeMatch": [
            {"criteria": criteria, "vulnerable": True, "versionStartIncluding": "2.0", "versionEndExcluding": "2.15.0"},
            {"criteria": criteria, "vulnerable": False, "versionStartExcluding": "1", "versionEndIncluding": "2"},
        ]}],
    }]}
    rules = applicability(raw)
    assert rules["configurations"] == raw["configurations"]
    assert len(rules["matches"]) == 2
    assert rules["matches"][0]["logical_context"][0]["operator"] == "AND"
    assert rules["matches"][0]["logical_context"][1]["operator"] == "OR"
    assert rules["matches"][1]["vulnerable"] is False
    assert rules["warnings"][0]["boundary"] == "2.15.0"
    projected = enriched_cpes([{"criteria": criteria, "product_id": "product"}], rules)
    assert len(projected[0]["constraints"]) == 2
    assert projected[0]["constraints"][0]["versionEndExcluding"] == "2.15.0"
    assert projected[0]["constraints"][1]["versionEndIncluding"] == "2"


def test_real_nvd_fixture_rules_match_original_json_pointers():
    path = Path(__file__).resolve().parents[1] / "docs/evidence/codex_functional/nvd_CVE-2021-44228.json"
    raw = json.loads(path.read_text())["vulnerabilities"][0]["cve"]
    rules = applicability(raw)
    assert rules["configurations"] == raw["configurations"]
    assert any(w["boundary"] == "2.15.0" for w in rules["warnings"])
    for match in rules["matches"]:
        original = raw
        for part in match["source_path"].split("/")[1:]:
            original = original[int(part)] if isinstance(original, list) else original[part]
        assert all(match[k] == v for k, v in original.items())


@pytest.mark.parametrize("path,params", [
    ("/api/v1/vulnerabilities", {"unexpected_parameter": "qa"}),
    ("/api/v1/products/top", {"limit": 1}),
    ("/api/v1/cwes/top", {"limit": "bad"}),
    ("/api/v1/kpis", {"unexpected_parameter": "qa"}),
    ("/api/v1/graph/cve/CVE-2021-44228", {"limit": 1}),
    ("/api/v1/vulnerabilities", {"page": "2.0"}),
    ("/api/v1/vulnerabilities", {"view": "summary", "fields": "raw_cve"}),
    ("/api/v1/vulnerabilities", {"fields": "cvss"}),
    ("/api/v1/products/top", {"page": 2}),
    ("/api/v1/graph/cve/CVE-2021-44228", {"page_size": 251}),
    ("/api/v1/graph/cve/CVE-2021-44228", {"relationship_type": "ARBITRARY"}),
])
def test_api_contract_rejects_invalid_queries_without_database(path, params):
    assert TestClient(app).get(path, params=params).status_code == 422


def test_summary_projection_bounds_and_explicit_fields():
    projected = summary_projection()
    assert "raw_cve" not in projected and "cpes" not in projected
    assert projected["description"]["$substrCP"][2] == 512
    assert projected["cpe_count"]["$size"]
    assert summary_projection("cvss,severity") == {"_id": 0, "cve_id": 1, "cvss": 1, "severity": 1}


def test_product_catalog_cache_tie_break_and_snapshot_guard():
    calls = []
    stats = {"as_of": "snapshot-a", "total_cves": 3}
    products = [
        {"_id": "b", "cve_count": 2, "product": {"id": "b"}},
        {"_id": "a", "cve_count": 2, "product": {"id": "a"}},
    ]

    def aggregate(pipeline, **_options):
        calls.append(pipeline)
        return iter(products)

    mongo = SimpleNamespace(collection=SimpleNamespace(aggregate=aggregate), db=SimpleNamespace(kpis=SimpleNamespace(find_one=lambda *_args: dict(stats))))
    views = ReadViews(mongo)
    assert [p["id"] for p in views.product_catalog()] == ["a", "b"]
    assert views.product_catalog("snapshot-a") == views.product_catalog("snapshot-a")
    assert len(calls) == 1
    stats["as_of"] = "snapshot-b"
    with pytest.raises(HTTPException) as error:
        views.product_catalog("snapshot-a")
    assert error.value.status_code == 409
