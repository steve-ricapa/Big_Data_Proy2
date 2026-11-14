from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta


def calculate(rows, as_of=None):
    as_of = as_of or datetime.now(UTC)
    severity, months, cwes, products, vendors, versions = (
        Counter(),
        Counter(),
        Counter(),
        Counter(),
        Counter(),
        defaultdict(lambda: [0, 0.0]),
    )
    total = recent = rejected = 0
    for row in rows:
        total += 1
        rejected += row.get("status") == "Rejected"
        severity[row["severity"]] += 1
        months[row["month"]] += 1
        cwes.update(set(row["cwes"]))
        products.update({p["id"] for p in row["products"]})
        vendors.update({p["vendor"] for p in row["products"]})
        if row.get("cvss"):
            versions[row["cvss"]["version"]][0] += 1
            versions[row["cvss"]["version"]][1] += row["cvss"]["score"]
        modified = datetime.fromisoformat(row["last_modified"])
        recent += as_of - timedelta(days=30) <= modified <= as_of
    return {
        "as_of": as_of.isoformat(),
        "total_cves": total,
        "rejected_cves": rejected,
        "severity": dict(severity),
        "severity_percent": {k: round(v * 100 / total, 4) for k, v in severity.items()}
        if total
        else {},
        "monthly": dict(sorted(months.items())),
        "top_cwes": cwes.most_common(20),
        "top_products": products.most_common(20),
        "top_vendors": vendors.most_common(20),
        "unique_affected_products": len(products),
        "cvss_by_version": {
            k: {"count": v[0], "average": round(v[1] / v[0], 4)}
            for k, v in versions.items()
        },
        "modified_last_30_days": recent,
        "notes": [
            "CVE no equivale a ataque confirmado",
            "Productos únicos no equivalen a registros CPE",
            "Promedios CVSS separados por versión; UNKNOWN no se imputa a cero",
        ],
    }
