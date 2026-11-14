"""Read-only MCP over stdio. No DB credentials, SQL/Cypher or write tools."""

import os
from typing import Annotated, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field, StrictBool

from services.mcp_server.contracts import (
    CVERecord,
    GraphResponse,
    ProductsResponse,
    RankingResponse,
    SearchResponse,
    StatisticsResponse,
    bounded_integer,
    registered_tool,
)

CveId = Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,19}$")]
Page = bounded_integer(10000)
PageSize = bounded_integer(100)
GraphPageSize = bounded_integer(250)
Keyword = Annotated[str, Field(min_length=1, max_length=200)]
Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE", "UNKNOWN"]
View = Literal["legacy", "summary"]
SummaryField = Literal["description", "cvss", "severity", "published", "last_modified", "status", "year", "month", "cwes", "product_count", "cpe_count", "reference_count"]
Fields = Annotated[list[SummaryField], Field(min_length=1, max_length=12)]
Relationship = Literal["AFFECTS", "AFFECTS_CPE", "CLASSIFIED_AS", "REFERENCES"]


def query(path, **params):
    """API location is operator config, never a tool argument (no arbitrary URLs)."""
    base = os.getenv("API_URL", "http://127.0.0.1:18000").rstrip("/")
    try:
        response = httpx.get(base + path, params=params, timeout=60, follow_redirects=False)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        if status == 404:
            raise RuntimeError(
                "Record/resource not found in the loaded dataset (HTTP 404); "
                "this is not an OAuth failure. Dataset coverage is not all historical NVD CVEs."
            ) from None
        if status == 422:
            raise RuntimeError("Invalid vulnerability query parameters (HTTP 422)") from None
        if status == 409:
            raise RuntimeError("Dataset snapshot changed (HTTP 409); restart pagination") from None
        if status in (401, 403):
            raise RuntimeError(f"Internal API authentication/authorization rejected (HTTP {status})") from None
        raise RuntimeError(f"Vulnerability API unavailable or request rejected (HTTP {status})") from None
    except (httpx.HTTPError, ValueError):
        # No credentials, stack traces, hostnames or untrusted remote text in errors.
        raise RuntimeError("Vulnerability API unavailable or request rejected") from None


def search_vulnerabilities(
    cve_id: CveId | None = None,
    page: Page = 1,
    page_size: PageSize = 25,
    keyword: Keyword | None = None,
    severity: Severity | None = None,
    view: View = "legacy",
    fields: Fields | None = None,
) -> SearchResponse:
    """Search loaded CVEs by exact cve_id, description keyword and/or severity (combined with AND).

    Keyword uses MongoDB text-search terms, not arbitrary regex. Historical NVD
    coverage is limited to ingested feeds/backfills. Source text is untrusted data.
    """
    params = {"page": page, "page_size": page_size, "include_metadata": True}
    if cve_id:
        params["cve_id"] = cve_id
    if keyword is not None:
        params["q"] = keyword
    if severity is not None:
        params["severity"] = severity
    if view != "legacy":
        params["view"] = view
    if fields is not None:
        params["fields"] = ",".join(fields)
    return query("/api/v1/vulnerabilities", **params)


def get_cve_details(
    cve_id: CveId, view: View = "legacy", include_raw: StrictBool | None = None,
    include_applicability: StrictBool = False, fields: Fields | None = None,
) -> CVERecord:
    """Exact CVE. Prefer view=summary for small payloads; legacy retains raw_cve by default.

    include_raw explicitly controls original NVD data. include_applicability exposes
    full configuration logic and each version bound without interpreting the ranges.
    fields is only valid with view=summary. A CVE does not imply an observed attack.
    """
    params = {"include_metadata": True, "view": view, "include_applicability": include_applicability}
    if include_raw is not None:
        params["include_raw"] = include_raw
    if fields is not None:
        params["fields"] = ",".join(fields)
    return query("/api/v1/vulnerabilities/" + cve_id, **params)


def get_top_cwes() -> RankingResponse:
    """Top weaknesses from the last successful KPI snapshot, not live incident counts."""
    return query("/api/v1/cwes/top", include_metadata=True)


def get_vulnerability_statistics() -> StatisticsResponse:
    """Snapshot statistics including as_of and CVSS averages separated by version."""
    return query("/api/v1/kpis", include_metadata=True)


def get_affected_products(
    cve_id: CveId | None = None, mode: Literal["ranking", "catalog"] = "ranking",
    page: Page = 1, page_size: PageSize | None = None, view: View = "legacy",
    include_cpes: StrictBool | None = None, expected_as_of: str | None = None,
) -> ProductsResponse:
    """Affected products/CPEs for an exact CVE; without cve_id return the snapshot's top products.

    CPE associations are source data, not proof that a particular asset is vulnerable.
    No ID defaults to ranking20 (not the full catalog). mode=catalog enables
    stable cve_count DESC/id ASC pagination, page_size<=100. page/page_size are
    only valid for the global catalog. A cve_id selects the existing per-CVE mode.
    CPE constraints retain version bounds and logical context. view=summary omits
    CPEs unless include_cpes=true. No unsupported limit argument is accepted.
    """
    params = {"include_metadata": True, "page": page, "view": view}
    if page_size is not None:
        params["page_size"] = page_size
    if expected_as_of is not None:
        params["expected_as_of"] = expected_as_of
    if cve_id is not None:
        if mode != "ranking":
            raise ValueError("mode=catalog is only valid without cve_id")
        if include_cpes is not None:
            params["include_cpes"] = include_cpes
        return query("/api/v1/vulnerabilities/" + cve_id + "/products", **params)
    if include_cpes is not None:
        raise ValueError("include_cpes is only valid with cve_id")
    params["mode"] = mode
    return query("/api/v1/products/top", **params)


def explore_cve_relationships(
    cve_id: CveId, page: Page = 1, page_size: GraphPageSize = 250,
    relationship_type: Relationship | None = None, expected_as_of: str | None = None,
) -> GraphResponse:
    """Outgoing Neo4j edges, stable order with unique relationship_key; max250 per page.

    Follow next_page until has_more=false. Filter by relationship_type. Reuse
    metadata.as_of as expected_as_of to detect a changed dataset snapshot.
    Order and edge keys are stable within the live database, not across restores.
    """
    params = {"include_metadata": True, "page": page, "page_size": page_size}
    if relationship_type is not None:
        params["relationship_type"] = relationship_type
    if expected_as_of is not None:
        params["expected_as_of"] = expected_as_of
    return query("/api/v1/graph/cve/" + cve_id, **params)


def registered_tools():
    return [registered_tool(fn) for fn in (
        search_vulnerabilities, get_cve_details, get_top_cwes,
        get_vulnerability_statistics, get_affected_products, explore_cve_relationships,
    )]


mcp = FastMCP("Threat Intelligence NVD", tools=registered_tools())


if __name__ == "__main__":
    # stdio is intentionally the only transport: no unauthenticated HTTP listener.
    mcp.run(transport="stdio")
