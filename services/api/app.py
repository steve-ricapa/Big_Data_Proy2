"""Local read-only API. Database details and credentials never enter error responses."""

import json
import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse

from services.api.views import (
    ReadViews,
    applicability,
    enrich_graph,
    enriched_cpes,
    read_views,
    summary_projection,
)
from threat_intelligence.common.config import settings
from threat_intelligence.databases.mongodb import Mongo
from threat_intelligence.databases.neo4j import Neo

logger = logging.getLogger(__name__)
CVE_PATTERN = r"^CVE-\d{4}-\d{4,19}$"


@asynccontextmanager
async def lifespan(app):
    app.state.mongo = Mongo(settings())
    app.state.graph = Neo(settings())
    app.state.read_views = ReadViews(app.state.mongo)
    yield
    app.state.mongo.close()
    app.state.graph.close()


app = FastAPI(title="Threat Intelligence Platform", version="1.0", lifespan=lifespan)


@app.middleware("http")
async def strict_query_parameters(request: Request, call_next):
    path = request.url.path
    allowed = None
    if path == "/api/v1/vulnerabilities":
        allowed = {"cve_id", "year", "severity", "cwe", "q", "published_from", "published_to", "page", "page_size", "view", "fields", "include_metadata"}
    elif path.startswith("/api/v1/vulnerabilities/"):
        allowed = ({"page", "page_size", "view", "include_cpes", "expected_as_of", "include_metadata"} if path.endswith("/products") else {"view", "include_raw", "include_applicability", "fields", "include_metadata"})
    elif path.startswith("/api/v1/graph/cve/"):
        allowed = {"page", "page_size", "relationship_type", "expected_as_of", "include_metadata"}
    elif path == "/api/v1/products/top":
        allowed = {"mode", "page", "page_size", "view", "expected_as_of", "include_metadata"}
    elif path in ("/api/v1/kpis", "/api/v1/cwes/top"):
        allowed = {"include_metadata"}
    elif path.startswith("/api/v1/"):
        allowed = set()
    if allowed is not None:
        keys = list(request.query_params)
        unknown = sorted(set(keys) - allowed)
        duplicate = any(len(request.query_params.getlist(key)) > 1 for key in keys)
        bad_integer = any(key in request.query_params and not (request.query_params[key].isascii() and request.query_params[key].isdecimal()) for key in ("page", "page_size"))
        if unknown or duplicate or bad_integer:
            return JSONResponse(status_code=422, content={"detail": "Unknown/duplicate query parameter or invalid integer encoding", "unknown_parameters": [key[:64] for key in unknown]})
    return await call_next(request)


@app.exception_handler(Exception)
async def database_error(request: Request, error: Exception):
    logger.error("Request failed: %s", type(error).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Data service unavailable; inspect local service health."},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(request: Request):
    request.app.state.mongo.ping()
    request.app.state.graph.ping()
    # A read path must not create keyspaces/tables or require schema privileges.
    from threat_intelligence.databases.cassandra import Cassandra

    cassandra = Cassandra(settings(), initialize_schema=False)
    try:
        cassandra.ping()
    finally:
        cassandra.close()
    return {"status": "ready", "checked": ["mongodb", "cassandra", "neo4j"]}


@app.get("/api/v1/kpis")
def kpis(request: Request, include_metadata: bool = False):
    value = request.app.state.mongo.db.kpis.find_one({"_id": "latest"}, {"_id": 0})
    if not value:
        raise HTTPException(404, "No successful KPI snapshot; run the pipeline.")
    if include_metadata:
        value["metadata"] = read_views(request).metadata(count_unit="distinct loaded CVE IDs")
    return value


@app.get("/api/v1/vulnerabilities")
def search(
    request: Request,
    cve_id: str | None = Query(None, pattern=r"^CVE-\d{4}-\d{4,19}$"),
    year: int | None = Query(None, ge=1999, le=2100),
    severity: str | None = Query(
        None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW|NONE|UNKNOWN)$"
    ),
    cwe: str | None = Query(None, pattern=r"^CWE-\d+$"),
    q: str | None = Query(None, min_length=1, max_length=200),
    published_from: date | None = None,
    published_to: date | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(25, ge=1, le=100),
    view: Literal["legacy", "summary"] = "legacy",
    fields: str | None = Query(None, max_length=300),
    include_metadata: bool = False,
):
    if published_from and published_to and published_from > published_to:
        raise HTTPException(422, "published_from must be on or before published_to")
    query = {
        k: v
        for k, v in {
            "cve_id": cve_id,
            "year": year,
            "severity": severity,
            "cwes": cwe,
        }.items()
        if v is not None
    }
    if q is not None:
        q = q.strip()
        if not q:
            raise HTTPException(422, "q must contain a search term")
        # Native indexed text search; never interpret user input as regex/operators.
        query["$text"] = {"$search": q}
    if published_from or published_to:
        query["published"] = {}
        if published_from:
            query["published"]["$gte"] = published_from.isoformat()
        if published_to:
            query["published"]["$lte"] = published_to.isoformat() + "T23:59:59.999999+00:00"
    if fields is not None and view != "summary":
        raise HTTPException(422, "fields requires view=summary")
    projection = summary_projection(fields) if view == "summary" else {"_id": 0, "raw_cve": 0}
    collection = request.app.state.mongo.collection
    cursor = (
        collection.find(query, projection)
        .sort("cve_id", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
        .max_time_ms(10000)
    )
    result = {
        "items": list(cursor),
        # Empty count otherwise scans ~1 GB of documents on a cold small VM.
        "total": collection.count_documents(
            query, maxTimeMS=10000, **({"hint": "cve_id_1"} if not query else {})
        ),
        "page": page,
        "page_size": page_size,
    }
    if include_metadata:
        result["metadata"] = read_views(request).metadata(
            ordering="cve_id ASC", view=view, description_limit=512 if view == "summary" else None,
            search_semantics="MongoDB English text search: unquoted positive terms OR, quoted phrase, minus exclusion; case/diacritic insensitive. Other filters AND. Special characters are not literal substring search.",
        )
    return result


@app.get("/api/v1/vulnerabilities/{cve_id}")
def detail(
    request: Request, cve_id: str = Path(pattern=CVE_PATTERN),
    view: Literal["legacy", "summary"] = "legacy", include_raw: bool | None = None,
    include_applicability: bool = False, fields: str | None = Query(None, max_length=300),
    include_metadata: bool = False,
):
    if fields is not None and view != "summary":
        raise HTTPException(422, "fields requires view=summary")
    raw_requested = include_raw if include_raw is not None else view == "legacy"
    projection = summary_projection(fields) if view == "summary" else {"_id": 0}
    if raw_requested and view == "summary":
        projection["raw_cve"] = 1
    elif not raw_requested and view == "legacy":
        projection["raw_cve"] = 0
    row = request.app.state.mongo.collection.find_one({"cve_id": cve_id}, projection)
    if row is None:
        raise HTTPException(404, "CVE not found")
    if include_applicability or include_metadata:
        source = row.get("raw_cve")
        if source is None:
            original = request.app.state.mongo.collection.find_one({"cve_id": cve_id}, {"_id": 0, "raw_cve": 1})
            source = original.get("raw_cve", {})
        rules = applicability(source)
        if include_applicability:
            row["applicability"] = rules
        if include_metadata:
            row["metadata"] = read_views(request).metadata(view=view, raw_included=raw_requested, applicability_warnings=rules["warnings"], legacy_cpe_notice="CPE identity alone is not an all-versions claim; request include_applicability=true for preserved NVD Boolean configuration rules.")
    return row


@app.get("/api/v1/vulnerabilities/{cve_id}/products")
def affected_products(
    request: Request, cve_id: str = Path(pattern=CVE_PATTERN), page: int = Query(1, ge=1, le=10000),
    page_size: int | None = Query(None, ge=1, le=100), view: Literal["legacy", "summary"] = "legacy",
    include_cpes: bool | None = None, expected_as_of: str | None = None, include_metadata: bool = False,
):
    if page != 1 or page_size is not None:
        raise HTTPException(422, "page/page_size are only supported for the global product catalog")
    if expected_as_of is not None:
        read_views(request).check_snapshot(expected_as_of)
    row = request.app.state.mongo.collection.find_one(
        {"cve_id": cve_id}, {"_id": 0, "cve_id": 1, "products": 1, "cpes": 1, "raw_cve": 1}
    )
    if row is None:
        raise HTTPException(404, "CVE not found")
    rules = applicability(row.get("raw_cve", {}))
    cpes_requested = include_cpes if include_cpes is not None else view == "legacy"
    result = {"cve_id": cve_id, "mode": "per_cve", "items": row.get("products", []), "cpes": enriched_cpes(row.get("cpes", []), rules) if cpes_requested else []}
    if include_metadata:
        result["metadata"] = read_views(request).metadata(
            count_unit="part/vendor/product identity for this CVE, not versions/assets", product_count=len(row.get("products", [])),
            cpe_count=len(row.get("cpes", [])), cpes_included=cpes_requested,
            applicability_warnings=rules["warnings"],
            applicability_source="raw_cve.configurations; logical_context/source_path retained per CPE constraint; include_applicability=true on detail exposes the exact tree",
        )
    return result


@app.get("/api/v1/cwes/top")
def cwes(request: Request, include_metadata: bool = False):
    items = kpis(request)["top_cwes"]
    if include_metadata:
        return {"items": items, "metadata": read_views(request).metadata(count_unit="distinct CVEs per CWE", ranking_limit=20, mode="snapshot_ranking_only", population_includes_rejected=True)}
    return items


@app.get("/api/v1/analytics/cassandra/snapshot")
def cassandra_snapshot():
    """Read Cassandra itself, not a Mongo snapshot labelled as Cassandra."""
    from threat_intelligence.databases.cassandra import Cassandra

    sink = Cassandra(settings(), initialize_schema=False)
    try:
        row = sink.session.execute(
            "SELECT payload FROM kpi_snapshots WHERE snapshot_id=%s", ("latest",)
        ).one()
        if row is None:
            raise HTTPException(404, "No Cassandra KPI snapshot; run the pipeline.")
        return {"source": "cassandra", "snapshot": json.loads(row.payload)}
    finally:
        sink.close()


@app.get("/api/v1/products/top")
def products(
    request: Request, mode: Literal["ranking", "catalog"] = "ranking",
    page: int = Query(1, ge=1, le=10000), page_size: int | None = Query(None, ge=1, le=100),
    view: Literal["legacy", "summary"] = "legacy", expected_as_of: str | None = None,
    include_metadata: bool = False,
):
    if view != "legacy":
        raise HTTPException(422, "view applies only to per-CVE product responses")
    if mode == "ranking":
        if page != 1 or page_size is not None:
            raise HTTPException(422, "Pagination requires mode=catalog; ranking is the snapshot top20")
        if expected_as_of is not None:
            read_views(request).check_snapshot(expected_as_of)
        stats = kpis(request)
        items = stats["top_products"]
        if include_metadata:
            return {"items": items, "mode": "ranking", "metadata": read_views(request).metadata(count_unit="distinct CVEs per product identity", ranking_limit=20, catalog_total=stats["unique_affected_products"], continuation="Use mode=catalog to enumerate all identities")}
        return items
    size = page_size or 25
    catalog = read_views(request).product_catalog(expected_as_of)
    start = (page - 1) * size
    total = len(catalog)
    return {"mode": "catalog", "items": catalog[start:start + size], "total": total, "page": page, "page_size": size,
            "next_page": page + 1 if start + size < total else None, "has_more": start + size < total,
            "metadata": read_views(request).metadata(count_unit="distinct product identities; cve_count counts distinct CVE IDs", ordering="cve_count DESC, id ASC", cache="immutable catalog for one KPI cut per API process")}


@app.get("/api/v1/graph/cve/{cve_id}")
def graph(
    request: Request, cve_id: str = Path(pattern=CVE_PATTERN), page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(250, ge=1, le=250),
    relationship_type: Literal["AFFECTS", "AFFECTS_CPE", "CLASSIFIED_AS", "REFERENCES"] | None = None,
    expected_as_of: str | None = None, include_metadata: bool = False,
):
    if expected_as_of is not None:
        read_views(request).check_snapshot(expected_as_of)
    counts = request.app.state.graph.query(
        "MATCH (c:CVE {id:$id}) OPTIONAL MATCH (c)-[r]->() "
        "RETURN c.id AS cve_id,count(r) AS n, "
        "sum(CASE WHEN r IS NOT NULL AND ($relationship_type IS NULL OR type(r)=$relationship_type) THEN 1 ELSE 0 END) AS filtered",
        id=cve_id, relationship_type=relationship_type,
    )
    if not counts:
        raise HTTPException(404, "CVE not found in graph")
    total, filtered = counts[0]["n"], counts[0]["filtered"]
    result = request.app.state.graph.query(
        "MATCH (c:CVE {id:$id}) MATCH (c)-[r]->(n) WHERE $relationship_type IS NULL OR type(r)=$relationship_type "
        "RETURN c.id AS cve_id, type(r) AS relationship, labels(n) AS labels, properties(n) AS entity, elementId(r) AS relationship_key "
        "ORDER BY CASE type(r) WHEN 'AFFECTS' THEN 0 WHEN 'CLASSIFIED_AS' THEN 1 "
        "WHEN 'AFFECTS_CPE' THEN 2 ELSE 3 END, coalesce(n.id,n.url,''), elementId(r) SKIP $skip LIMIT $size",
        id=cve_id, relationship_type=relationship_type, skip=(page - 1) * page_size, size=page_size,
    )
    source = request.app.state.mongo.collection.find_one({"cve_id": cve_id}, {"_id": 0, "raw_cve": 1})
    rules = applicability(source.get("raw_cve", {}) if source else {})
    result = enrich_graph(result, rules)
    response = {"items": result, "limit": page_size, "total_relationships": total, "truncated": filtered > len(result),
                "total": filtered, "page": page, "page_size": page_size, "has_more": page * page_size < filtered,
                "next_page": page + 1 if page * page_size < filtered else None}
    if include_metadata:
        response["metadata"] = read_views(request).metadata(relationship_type=relationship_type, count_unit="outgoing Neo4j edges (not CVEs)",
            ordering="relationship priority AFFECTS, CLASSIFIED_AS, AFFECTS_CPE, REFERENCES; entity identity ASC; relationship_key ASC",
            applicability_source="CVE-specific Mongo raw NVD configurations; stored global Neo4j CPE identities are not version assertions", applicability_warnings=rules["warnings"])
    return response


@app.get("/api/v1/pipeline/status")
def pipeline(request: Request):
    manifests = sorted(
        settings().staging_dir.glob("*/run.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if manifests:
        try:
            value = json.loads(manifests[0].read_text(encoding="utf-8"))
            stages = value.get("stages", {})
            value["status"] = (
                "FAILED"
                if any(s.get("status") == "FAILED" for s in stages.values())
                else "SUCCESS"
                if "verify" in stages
                else "IN_PROGRESS_OR_INTERRUPTED"
            )
            return value
        except (OSError, ValueError):
            logger.warning(
                "Cannot read latest run manifest; falling back to verified run"
            )
    row = request.app.state.mongo.db.pipeline_runs.find_one(
        {}, {"_id": 0}, sort=[("started_at", -1)]
    )
    return row or {"status": "No verified run recorded"}
