import hashlib
import json
import math
import re
from datetime import UTC, datetime


def date(value):
    parsed = datetime.fromisoformat(value)
    return (
        parsed.replace(tzinfo=parsed.tzinfo or UTC)
        .astimezone(UTC)
        .isoformat(timespec="microseconds")
    )


def cpe_parts(value):
    # CPE escaped colons must not split vendor/product components.
    parts, current, escaped = [], [], False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts if len(parts) == 13 and parts[:2] == ["cpe", "2.3"] else None


def matches(nodes):
    for node in nodes:
        yield from node.get("cpeMatch", [])
        yield from matches(node.get("nodes", []))
        yield from matches(node.get("children", []))


def normalize(entry):
    cve = entry.get("cve", entry)
    cve_id = cve.get("id", "")
    if not re.fullmatch(r"CVE-\d{4}-\d{4,19}", cve_id):
        raise ValueError("invalid_cve_id")
    published, modified = date(cve["published"]), date(cve["lastModified"])
    descriptions = cve.get("descriptions", [])
    description = next(
        (d["value"] for d in descriptions if d.get("lang") == "en"),
        next((d.get("value", "") for d in descriptions), ""),
    )
    selected = None
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for metric in sorted(
            cve.get("metrics", {}).get(key, []),
            key=lambda m: (m.get("type") != "Primary", m.get("source", "")),
        ):
            data = metric.get("cvssData", {})
            score = data.get("baseScore")
            if (
                isinstance(score, (int, float))
                and not isinstance(score, bool)
                and math.isfinite(score)
                and 0 <= score <= 10
            ):
                version = str(
                    data.get(
                        "version",
                        {
                            "cvssMetricV40": "4.0",
                            "cvssMetricV31": "3.1",
                            "cvssMetricV30": "3.0",
                            "cvssMetricV2": "2.0",
                        }[key],
                    )
                )
                severity = (
                    data.get("baseSeverity") or metric.get("baseSeverity") or ""
                ).upper()
                if severity not in {"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                    severity = (
                        ("HIGH" if score >= 7 else "MEDIUM" if score >= 4 else "LOW")
                        if version == "2.0"
                        else (
                            "CRITICAL"
                            if score >= 9
                            else "HIGH"
                            if score >= 7
                            else "MEDIUM"
                            if score >= 4
                            else "LOW"
                            if score > 0
                            else "NONE"
                        )
                    )
                selected = {
                    "version": version,
                    "score": float(score),
                    "severity": severity,
                    "vector": data.get("vectorString"),
                    "source": metric.get("source"),
                }
                break
        if selected:
            break
    cwes = sorted(
        {
            d["value"]
            for w in cve.get("weaknesses", [])
            for d in w.get("description", [])
            if re.fullmatch(r"CWE-\d+", d.get("value", ""))
        }
    )
    products, cpes = {}, {}
    for match in matches(cve.get("configurations", [])):
        if match.get("vulnerable") is not True:
            continue
        criteria = match.get("criteria", "")
        parts = cpe_parts(criteria)
        if not parts or parts[3] in ("*", "-", "") or parts[4] in ("*", "-", ""):
            continue
        product_id = json.dumps(parts[2:5], separators=(",", ":"))
        products[product_id] = {
            "id": product_id,
            "part": parts[2],
            "vendor": parts[3],
            "product": parts[4],
        }
        cpes[criteria] = {"criteria": criteria, "product_id": product_id}
    document = {
        "cve_id": cve_id,
        "published": published,
        "last_modified": modified,
        "month": published[:7],
        "year": int(published[:4]),
        "status": cve.get("vulnStatus", "Unknown"),
        "description": description,
        "cvss": selected,
        "severity": selected["severity"] if selected else "UNKNOWN",
        "cwes": cwes,
        "products": sorted(products.values(), key=lambda p: p["id"]),
        "cpes": sorted(cpes.values(), key=lambda p: p["criteria"]),
        "references": sorted(
            {
                r["url"]
                for r in cve.get("references", [])
                if isinstance(r.get("url"), str)
            }
        ),
        "raw_cve": cve,
    }
    document["content_hash"] = hashlib.sha256(
        json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    return document
