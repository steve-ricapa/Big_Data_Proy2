"""Read-only projections: no historical rewrites and no inferred version ranges."""
import copy
import json
import re
import threading

from fastapi import HTTPException

from threat_intelligence.transformations.normalize import cpe_parts

SUMMARY_FIELDS = {
    "description", "cvss", "severity", "published", "last_modified", "status",
    "year", "month", "cwes", "product_count", "cpe_count", "reference_count",
}
SOURCE = "NIST NVD CVE API 2.0"


def summary_projection(fields=None):
    selected = SUMMARY_FIELDS if fields is None else set(fields.split(","))
    if not selected or not selected <= SUMMARY_FIELDS:
        raise HTTPException(422, "fields must name supported summary fields")
    projection = {"_id": 0, "cve_id": 1}
    for field in selected:
        if field.endswith("_count"):
            array = {"product_count": "products", "cpe_count": "cpes", "reference_count": "references"}[field]
            projection[field] = {"$size": {"$ifNull": ["$" + array, []]}}
        elif field == "description":
            projection[field] = {"$substrCP": ["$description", 0, 512]}
            projection["description_truncated"] = {"$gt": [{"$strLenCP": "$description"}, 512]}
        else:
            projection[field] = 1
    return projection


def applicability(raw):
    """Keep every cpeMatch occurrence, including environmental/nonvulnerable ones."""
    tree = copy.deepcopy(raw.get("configurations", []))
    matches = []

    def walk(node, path, parents):
        context = {"path": path, **{k: node[k] for k in ("operator", "negate") if k in node}}
        contexts = [*parents, context]
        for index, match in enumerate(node.get("cpeMatch", [])):
            entry = copy.deepcopy(match)
            entry.update(source_path=f"{path}/cpeMatch/{index}", logical_context=contexts)
            parts = cpe_parts(match.get("criteria", ""))
            if parts:
                entry["product_id"] = json.dumps(parts[2:5], separators=(",", ":"))
            matches.append(entry)
        for key in ("nodes", "children"):
            for index, child in enumerate(node.get(key, [])):
                walk(child, f"{path}/{key}/{index}", contexts)

    for index, configuration in enumerate(tree):
        walk(configuration, f"/configurations/{index}", [])
    description = next((v.get("value", "") for v in raw.get("descriptions", []) if v.get("lang") == "en"), "")
    boundaries = sorted({m["versionEndExcluding"] for m in matches if m.get("versionEndExcluding") and re.search(r"(?<![\w.])" + re.escape(m["versionEndExcluding"]) + r"(?![\w.])", description)})
    warnings = [{
        "code": "description_mentions_excluded_boundary", "boundary": version,
        "message": "Description mentions this version while CPE has an exclusive bound. Preserve both; do not automatically resolve applicability.",
    } for version in boundaries]
    return {
        "source": SOURCE, "cve_id": raw.get("id"), "source_last_modified": raw.get("lastModified"),
        "configurations": tree, "matches": matches, "warnings": warnings,
        "interpretation": "Preserved NVD Boolean tree; flat matches are not an independent all-versions assertion.",
    }


def enriched_cpes(cpes, rules):
    by_criteria = {}
    for match in rules["matches"]:
        by_criteria.setdefault(match.get("criteria"), []).append(match)
    return [{**cpe, "constraints": by_criteria.get(cpe["criteria"], []), "identity_is_not_version_assertion": True} for cpe in cpes]


def enrich_graph(rows, rules):
    by_criteria = {}
    for match in rules["matches"]:
        by_criteria.setdefault(match.get("criteria"), []).append(match)
    for row in rows:
        entity = row.get("entity")
        if not entity:
            continue
        if row.get("relationship") == "AFFECTS_CPE":
            entity["constraints"] = by_criteria.get(entity.get("id"), [])
            entity["identity_is_not_version_assertion"] = True
        elif row.get("relationship") == "AFFECTS":
            entity["version_applicability_reference"] = "CVE-specific NVD configuration/CPE rules, not the shared product identity"
    return rows


class ReadViews:
    """Single-snapshot bounded process cache. Never stores tokens or writes data."""

    def __init__(self, mongo):
        self.mongo = mongo
        self.lock = threading.RLock()
        self.as_of = None
        self.coverage = None
        self.catalog = None

    def snapshot(self):
        stats = self.mongo.db.kpis.find_one({"_id": "latest"}, {"_id": 0})
        if not stats:
            raise HTTPException(404, "No verified KPI snapshot")
        with self.lock:
            if stats["as_of"] != self.as_of:
                self.as_of = stats["as_of"]
                self.coverage = None
                self.catalog = None
        return stats

    def check_snapshot(self, expected):
        stats = self.snapshot()
        if expected is not None and expected != stats["as_of"]:
            raise HTTPException(409, "Dataset snapshot changed; restart pagination")
        return stats

    def metadata(self, **extra):
        stats = self.snapshot()
        with self.lock:
            if self.coverage is None:
                years = list(self.mongo.collection.aggregate([
                    {"$group": {"_id": "$year", "count": {"$sum": 1}, "first_published": {"$min": "$published"}, "last_published": {"$max": "$published"}}},
                    {"$sort": {"_id": 1}},
                ], maxTimeMS=30000))
                last = self.mongo.db.pipeline_runs.find_one({"status": "SUCCESS"}, {"_id": 0, "started_at": 1, "status": 1}, sort=[("started_at", -1)])
                self.coverage = {
                    "status": "partial", "is_complete_nvd_history": False,
                    "observed_publication_years": [{"year": v["_id"], **{k: v[k] for k in ("count", "first_published", "last_published")}} for v in years],
                    "missing_example": {"cve_id": "CVE-2021-45046", "present": self.mongo.collection.find_one({"cve_id": "CVE-2021-45046"}, {"_id": 0, "cve_id": 1}) is not None},
                    "last_verified_ingest": last,
                    "global_nvd_population": None,
                    "notice": "Observed loaded records, not a claim of complete coverage for these years. No on-read backfill.",
                }
            coverage = copy.deepcopy(self.coverage)
        self.check_snapshot(stats["as_of"])
        return {
            "as_of": stats["as_of"], "population": stats["total_cves"], "source": SOURCE,
            "coverage": coverage,
            "cvss_selection": "Preferred available 4.0,3.1,3.0,2.0; selected source/vector in each CVE.cvss. Versions are not averaged together.",
            "metric_definitions": {
                "rejected_cves": "Count of loaded CVEs whose NVD status is Rejected; included in population, not deletions or failed imports.",
                "product_cve_count": "Distinct CVE IDs associated with a part/vendor/product identity extracted from vulnerable CPEs; not number of versions/assets.",
                "cwe_cve_count": "Distinct loaded CVEs associated with the CWE; multi-label counts are not disjoint.",
            },
            "consistency": "Read committed; as_of is the last KPI cut, not a distributed MVCC snapshot. Restart paging if ingestion/restoration changes the dataset.",
            **extra,
        }

    def product_catalog(self, expected_as_of=None):
        stats = self.check_snapshot(expected_as_of)
        with self.lock:
            if self.catalog is None:
                rows = self.mongo.collection.aggregate([
                    {"$unwind": "$products"},
                    {"$group": {"_id": {"product": "$products.id", "cve": "$cve_id"}, "product": {"$first": "$products"}}},
                    {"$group": {"_id": "$_id.product", "cve_count": {"$sum": 1}, "product": {"$first": "$product"}}},
                ], allowDiskUse=True, maxTimeMS=45000)
                self.catalog = sorted(
                    ({**v["product"], "cve_count": v["cve_count"]} for v in rows),
                    key=lambda v: (-v["cve_count"], v["id"]),
                )
            result = [dict(v) for v in self.catalog]
        # Do not return a list built for an already changed KPI snapshot.
        self.check_snapshot(stats["as_of"])
        return result


def read_views(request):
    if not hasattr(request.app.state, "read_views"):
        request.app.state.read_views = ReadViews(request.app.state.mongo)
    return request.app.state.read_views
