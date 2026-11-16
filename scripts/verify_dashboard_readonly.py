"""Read-only Streamlit integration: real HTTP data, all views and filter/graph UI.

Run where API_URL is reachable. No database writes, CLI pipeline or MCP calls.
An optional --source supplies candidate dashboard Python over stdin for canary
testing; otherwise the installed dashboard file is exercised.
"""
import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest


def verify(base, source=None):
    os.environ["API_URL"] = base
    client = httpx.Client(base_url=base, timeout=60)
    result = {"at": datetime.now(UTC).isoformat(), "method": "Streamlit AppTest -> real HTTP API", "writes": False, "cases": []}

    def check(name, passed, observation=None):
        result["cases"].append({"id": name, "status": "PASS" if passed else "FAIL", "observation": observation})
        if not passed:
            raise AssertionError(name)

    def get(path, **params):
        response = client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def clean():
        assert not at.exception and not at.error

    def select(label, value):
        next(widget for widget in at.selectbox if widget.label == label).set_value(value)

    def text(label, value):
        next(widget for widget in at.text_input if widget.label == label).set_value(value)

    def number(label, value):
        next(widget for widget in at.number_input if widget.label == label).set_value(value)

    def submit(label):
        next(button for button in at.button if button.label == label).click().run()
        clean()

    try:
        stats = get("/api/v1/kpis")
        result["as_of"] = stats["as_of"]
        at = AppTest.from_string(source, default_timeout=60) if source else AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "services/dashboard/app.py"), default_timeout=60,
        )
        at.run()
        clean()
        metrics = {m.label: m.value for m in at.metric}
        check("overview_four_live_metrics", metrics == {
            "CVE únicos": f"{stats['total_cves']:,}", "Críticos": f"{stats['severity'].get('CRITICAL', 0):,}",
            "Modificados en 30 días": f"{stats['modified_last_30_days']:,}", "Productos identificables": f"{stats['unique_affected_products']:,}",
        }, metrics)
        # Streamlit chart protocol names vary by release. Inspect declared proto
        # types, not a historical fixed spelling that can silently count zero.
        chart_types = [element.type for element in at.main if "vega" in element.type]
        check("overview_severity_and_month_charts", len(chart_types) == 2, chart_types)
        at.sidebar.radio[0].set_value("Vulnerability Explorer").run()
        clean()
        check("explorer_live_total", any(f"{stats['total_cves']:,} resultados" in c.value for c in at.caption))
        control = get("/api/v1/vulnerabilities/CVE-2024-0001", view="summary")
        filters = {"cve_id": "CVE-2024-0001", "year": control["year"], "severity": control["severity"],
                   "published_from": control["published"][:10], "published_to": control["published"][:10]}
        text("CVE exacto", filters["cve_id"])
        select("Año de publicación", filters["year"])
        select("Severidad", filters["severity"])
        text("Publicado desde (AAAA-MM-DD)", filters["published_from"])
        text("Publicado hasta (AAAA-MM-DD)", filters["published_to"])
        cwe = next((v for v in control.get("cwes", []) if v.startswith("CWE-")), None)
        if cwe:
            filters["cwe"] = cwe
            text("CWE exacto", cwe)
        submit("Buscar")
        expected = get("/api/v1/vulnerabilities", **filters)
        check("explorer_combined_filters_and_detail", expected["total"] == 1 and list(at.dataframe[0].value["cve_id"]) == [control["cve_id"]] and bool(at.json))
        select("Severidad", "LOW" if control["severity"] != "LOW" else "HIGH")
        submit("Buscar")
        check("explorer_contradictory_filter_empty", len(at.dataframe[0].value) == 0 and not at.json)
        text("CVE exacto", "not-a-cve")
        submit("Buscar")
        check("explorer_invalid_filter_warning", bool(at.warning))
        at.sidebar.radio[0].set_value("Threat Analytics").run()
        clean()
        cassandra = get("/api/v1/analytics/cassandra/snapshot")
        check("analytics_cassandra_snapshot", cassandra["snapshot"] == stats and any(stats["as_of"] in c.value and "Cassandra" in c.value for c in at.caption) and not at.warning)
        for index, key in enumerate(("top_cwes", "top_vendors", "top_products")):
            check("analytics_" + key, at.dataframe[index].value.values.tolist() == [list(pair) for pair in stats[key]])
        at.sidebar.radio[0].set_value("Graph Intelligence").run()
        text("CVE", "CVE-2021-44228")
        select("Relaciones por página", 250)
        edge_keys = []
        expected_total = get("/api/v1/graph/cve/CVE-2021-44228", page_size=1)["total"]
        for page in range(1, (expected_total + 249) // 250 + 1):
            number("Página de relaciones", page)
            submit("Explorar relaciones")
            frame = at.dataframe[0].value
            edge_keys.extend(frame["relationship_key"].tolist())
            assert at.get("graphviz_chart")
        check("graph_all_pages_unique", len(edge_keys) == len(set(edge_keys)) == expected_total, {"total": expected_total})
        number("Página de relaciones", 1)
        select("Tipo de relación", "REFERENCES")
        submit("Explorar relaciones")
        check("graph_relationship_filter", set(at.dataframe[0].value["relationship"]) == {"REFERENCES"})
        check("graph_svg_source_and_pagination_caption", bool(at.get("graphviz_chart")) and any("relaciones filtradas" in c.value for c in at.caption))
        at.sidebar.radio[0].set_value("Data Pipeline").run()
        clean()
        check("pipeline_status_and_three_engine_readiness", len(at.json) == 2 and get("/ready")["status"] == "ready" and get("/api/v1/pipeline/status")["status"] == "SUCCESS")
        check("snapshot_unchanged_during_suite", get("/api/v1/kpis")["as_of"] == stats["as_of"])
        result["status"] = "PASS"
    except (AssertionError, httpx.HTTPError, KeyError, ValueError, IndexError, StopIteration) as error:
        result.update(status="FAIL", exception_type=type(error).__name__)
    finally:
        client.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true", help="Read candidate dashboard code from stdin")
    args = parser.parse_args()
    output = verify(os.getenv("API_URL", "http://127.0.0.1:18000"), sys.stdin.read() if args.source else None)
    print(json.dumps(output))
    raise SystemExit(0 if output["status"] == "PASS" else 1)
