"""Read-only real-HTTP integration suite; operator SDK dispatch, not OAuth E2E."""
import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.fastmcp.exceptions import ToolError

_root = Path(__file__).resolve().parents[1]
if (_root / "services").is_dir():
    sys.path.insert(0, str(_root))
from services.mcp_server import server


async def run():
    result = {"at": datetime.now(UTC).isoformat(), "transport": "FastMCP SDK -> real HTTP API -> production read-only DB identities", "oauth_e2e": "NOT_TESTED_IN_THIS_SUITE", "data_writes": False, "cases": [], "calls": 0}

    def check(label, passed, observation=None):
        result["cases"].append({"id": label, "status": "PASS" if passed else "FAIL", "observation": observation})
        assert passed, label

    async def call(name, arguments):
        result["calls"] += 1
        value = await server.mcp.call_tool(name, arguments)
        assert value.structuredContent is not None
        assert json.loads(value.content[0].text) == value.structuredContent
        return value.structuredContent, len(value.content[0].text)

    async def reject(label, name, arguments, expected="Invalid arguments"):
        try:
            await call(name, arguments)
        except ToolError as error:
            check(label, expected in str(error))
        else:
            check(label, False)

    try:
        tools = await server.mcp.list_tools()
        schemas = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in tools}
        result["schemas"] = schemas
        check("contract_six_closed_input_and_typed_output", len(tools) == 6 and all(t.inputSchema.get("additionalProperties") is False and t.outputSchema and t.outputSchema.get("properties") for t in tools))
        check("X01_full_input_schema", {"keyword", "severity", "cve_id", "page", "page_size"} <= schemas["search_vulnerabilities"]["inputSchema"]["properties"].keys())
        check("X02_products_schema", {"items", "cpes", "mode", "metadata"} <= schemas["get_affected_products"]["outputSchema"]["properties"].keys())
        stats, _ = await call("get_vulnerability_statistics", {})
        cut = stats["as_of"]
        result["snapshot"] = {"as_of": cut, "total_cves": stats["total_cves"], "severity": stats["severity"], "rejected_cves": stats["rejected_cves"]}
        result["reference_as_of"] = "2026-11-11T17:42:23.986620+00:00"
        if cut != result["reference_as_of"]:
            result["status"] = "BASELINE_REFRESH_REQUIRED"
            result["notice"] = "A legitimate ingestion changed the cut. Reconcile independent counts/source fixtures before reusing audit expectations. No production values are forced."
            return result
        check("statistics_and_definitions", stats["total_cves"] == sum(stats["severity"].values()) and "rejected_cves" in stats["metadata"]["metric_definitions"])
        check("coverage_not_complete", stats["metadata"]["coverage"]["is_complete_nvd_history"] is False)
        check("coverage_year_count_reconciliation", sum(v["count"] for v in stats["metadata"]["coverage"]["observed_publication_years"]) == stats["total_cves"])
        expected = {"keyword": ({"keyword": "log4j"}, 10), "severity": ({"severity": "CRITICAL", "page_size": 1}, stats["severity"]["CRITICAL"]), "combined": ({"keyword": "log4j", "severity": "CRITICAL"}, 2), "exact": ({"cve_id": "CVE-2021-44228"}, 1)}
        for label, (arguments, total) in expected.items():
            body, _ = await call("search_vulnerabilities", arguments)
            check("X01_" + label, body["total"] == total, {"total": body["total"]})
        first, _ = await call("search_vulnerabilities", {"keyword": "log4j", "page_size": 5, "view": "summary"})
        second, _ = await call("search_vulnerabilities", {"keyword": "log4j", "page_size": 5, "page": 2, "view": "summary"})
        search_ids = [row["cve_id"] for row in first["items"] + second["items"]]
        check("search_pages_stable_unique", len(search_ids) == len(set(search_ids)) == 10 and search_ids == sorted(search_ids))
        empty, _ = await call("search_vulnerabilities", {"keyword": "log4j", "page_size": 5, "page": 3, "view": "summary"})
        check("search_page_beyond_end", empty["total"] == 10 and empty["items"] == [])
        contradiction, _ = await call("search_vulnerabilities", {"cve_id": "CVE-2021-44228", "severity": "LOW", "view": "summary"})
        check("combined_filters_are_AND", contradiction["total"] == 0)
        negative_cases = [
            ("search_unknown", "search_vulnerabilities", {"unexpected_parameter": "qa"}),
            ("detail_unknown", "get_cve_details", {"cve_id": "CVE-2021-44228", "unexpected_parameter": "qa"}),
            ("products_limit", "get_affected_products", {"limit": 1}),
            ("graph_limit", "explore_cve_relationships", {"cve_id": "CVE-2021-44228", "limit": 1}),
            ("cwes_limit", "get_top_cwes", {"limit": 1}),
            ("cwes_bad_limit", "get_top_cwes", {"limit": "bad"}),
            ("statistics_unknown", "get_vulnerability_statistics", {"unexpected_parameter": "qa"}),
        ]
        for label, name, arguments in negative_cases:
            await reject("X03_" + label, name, arguments, "extra_forbidden")
        for label, arguments in [("page_zero", {"page": 0}), ("page_bool", {"page": True}), ("page_float", {"page": 2.0}), ("page_bad_string", {"page": "bad"}), ("page_string_bound", {"page": "10001"}), ("page_size_bound", {"page_size": 101}), ("invalid_severity", {"severity": "invalid"}), ("empty_fields", {"view": "summary", "fields": []}), ("unknown_projection", {"view": "summary", "fields": ["raw_cve"]})]:
            await reject(label, "search_vulnerabilities", arguments)
        coerced, _ = await call("search_vulnerabilities", {"page": "2", "page_size": 1, "view": "summary"})
        check("W02_documented_numeric_string", coerced["page"] == 2)
        special, _ = await call("search_vulnerabilities", {"keyword": "'\"%_*()[];--", "view": "summary", "page_size": 1})
        check("W01_text_semantics", "not literal" in special["metadata"]["search_semantics"], {"total": special["total"]})
        no_match, _ = await call("search_vulnerabilities", {"cve_id": "CVE-2021-45046", "view": "summary"})
        check("W03_missing_search", no_match["total"] == 0)
        await reject("W03_missing_detail", "get_cve_details", {"cve_id": "CVE-2021-45046"}, "HTTP 404")
        legacy, legacy_size = await call("get_cve_details", {"cve_id": "CVE-2021-44228"})
        source = json.loads(Path(os.environ["NVD_FIXTURE"]).read_text())["vulnerabilities"][0]["cve"]
        check("legacy_raw_source_preserved", legacy["raw_cve"] == source and legacy["cvss"]["score"] == 10 and legacy["cvss"]["version"] == "3.1")
        summary, summary_size = await call("get_cve_details", {"cve_id": "CVE-2021-44228", "view": "summary"})
        check("W07_summary_detail", "raw_cve" not in summary and summary_size < 15000, {"legacy_characters": legacy_size, "summary_characters": summary_size})
        projected, _ = await call("get_cve_details", {"cve_id": "CVE-2021-44228", "view": "summary", "fields": ["cvss", "severity"]})
        check("explicit_projection", set(projected) == {"cve_id", "cvss", "severity", "metadata"})
        no_raw, _ = await call("get_cve_details", {"cve_id": "CVE-2021-44228", "include_raw": False})
        check("raw_optional_without_shape_loss", "raw_cve" not in no_raw and no_raw["products"] == legacy["products"])
        rules, _ = await call("get_cve_details", {"cve_id": "CVE-2021-44228", "view": "summary", "include_applicability": True})
        rules = rules["applicability"]
        check("X04_exact_boolean_tree", rules["configurations"] == source["configurations"])
        for match in rules["matches"]:
            original = source
            for part in match["source_path"].split("/")[1:]:
                original = original[int(part)] if isinstance(original, list) else original[part]
            assert all(match[k] == value for k, value in original.items())
        check("X04_all_match_bounds_preserved", bool(rules["matches"]), {"source_match_occurrences": len(rules["matches"])})
        check("W06_unresolved_2_15_0_boundary", any(v["boundary"] == "2.15.0" for v in rules["warnings"]))
        products, _ = await call("get_affected_products", {"cve_id": "CVE-2021-44228"})
        check("X02_legacy_cve_product_counts", len(products["items"]) == 145 and len(products["cpes"]) == 358)
        check("X04_projected_constraints", any(m.get("versionEndExcluding") == "2.15.0" for c in products["cpes"] for m in c["constraints"]))
        small_products, _ = await call("get_affected_products", {"cve_id": "CVE-2021-44228", "view": "summary"})
        check("summary_products_explicit_omission", len(small_products["items"]) == 145 and small_products["cpes"] == [] and small_products["metadata"]["cpe_count"] == 358)
        ranking, _ = await call("get_affected_products", {})
        check("X02_legacy_ranking20", ranking["items"] == stats["top_products"] and ranking["metadata"]["ranking_limit"] == 20)
        cwes, _ = await call("get_top_cwes", {})
        check("W08_cwe_metadata_and_values", cwes["items"] == stats["top_cwes"] and cwes["metadata"]["as_of"] == cut)
        search100, summary100_size = await call("search_vulnerabilities", {"page_size": 100, "view": "summary"})
        check("W07_summary_search100", len(search100["items"]) == 100 and summary100_size < 180000, {"characters": summary100_size})
        old_shape, legacy100_size = await call("search_vulnerabilities", {"page_size": 100})
        check("legacy_search_compact_without_field_loss", len(old_shape["items"]) == 100 and "cpes" in old_shape["items"][0] and legacy100_size < 809565, {"characters": legacy100_size})
        ids = []
        types = Counter()
        edges = []
        page = 1
        while True:
            body, _ = await call("explore_cve_relationships", {"cve_id": "CVE-2021-44228", "page": page, "page_size": 73, "expected_as_of": cut})
            assert body["total"] == body["total_relationships"] == 559
            ids.extend(row["relationship_key"] for row in body["items"])
            types.update(row["relationship"] for row in body["items"])
            edges.extend(body["items"])
            if not body["has_more"]:
                assert body["next_page"] is None
                break
            assert body["next_page"] == page + 1
            page += 1
        check("N02_all_graph_edges_no_duplicates", len(ids) == len(set(ids)) == 559, {"pages": page, "counts": dict(types)})
        check("graph_type_distribution", dict(types) == {"AFFECTS": 145, "AFFECTS_CPE": 358, "CLASSIFIED_AS": 4, "REFERENCES": 52})
        check("X04_graph_cpe_constraints", any(m.get("versionEndExcluding") == "2.15.0" for edge in edges if edge["relationship"] == "AFFECTS_CPE" for m in edge["entity"]["constraints"]))
        for relationship, count in types.items():
            body, _ = await call("explore_cve_relationships", {"cve_id": "CVE-2021-44228", "relationship_type": relationship, "page_size": 5})
            check("graph_filter_" + relationship, body["total"] == count and all(e["relationship"] == relationship for e in body["items"]))
        a, _ = await call("explore_cve_relationships", {"cve_id": "CVE-2021-44228", "page": 3, "page_size": 73})
        b, _ = await call("explore_cve_relationships", {"cve_id": "CVE-2021-44228", "page": 3, "page_size": 73})
        check("repeat_graph_page_stable", a["items"] == b["items"])
        await reject("graph_snapshot_conflict", "explore_cve_relationships", {"cve_id": "CVE-2021-44228", "expected_as_of": "different-cut"}, "HTTP 409")
        catalog = []
        page = 1
        while True:
            body, _ = await call("get_affected_products", {"mode": "catalog", "page": page, "page_size": 100, "expected_as_of": cut})
            assert body["total"] == stats["unique_affected_products"]
            catalog.extend(body["items"])
            if not body["has_more"]:
                break
            page += 1
        keys = [row["id"] for row in catalog]
        check("N04_full_product_catalog_unique", len(keys) == len(set(keys)) == stats["unique_affected_products"], {"pages": page, "total": len(keys)})
        check("catalog_stable_order", catalog == sorted(catalog, key=lambda row: (-row["cve_count"], row["id"])))
        pairs = sorted((row["id"], row["cve_count"]) for row in catalog)
        result["catalog_reference"] = {"total": len(pairs), "id_count_sha256": hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()}
        await reject("catalog_snapshot_conflict", "get_affected_products", {"mode": "catalog", "expected_as_of": "different-cut"}, "HTTP 409")
        await reject("ranking_does_not_fake_pagination", "get_affected_products", {"page": 2}, "HTTP 422")
        control, _ = await call("get_cve_details", {"cve_id": "CVE-2024-0001", "view": "summary"})
        check("control_cvss_9_8", control["cvss"]["score"] == 9.8)
        graph, _ = await call("explore_cve_relationships", {"cve_id": "CVE-2024-0001"})
        check("control_graph4", graph["total"] == 4)
        check("W09_structured_content_equivalent", True, "Asserted for every successful call, not inferred from HTTP 200")
        result["status"] = "PASS_INTEGRATION_NOT_OAUTH_E2E"
    except Exception as error:  # noqa: BLE001 -- omit secret-bearing transport/response exception bodies
        result["status"] = "FAIL"
        result["exception_type"] = type(error).__name__
    return result


if __name__ == "__main__":
    output = asyncio.run(run())
    print(json.dumps(output))
    raise SystemExit(0 if output["status"] == "PASS_INTEGRATION_NOT_OAUTH_E2E" else 1)
