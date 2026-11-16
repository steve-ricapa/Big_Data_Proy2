"""UI regression against a local HTTP fixture, not claimed as cloud evidence."""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from scripts.verify_dashboard_readonly import verify


def test_five_views_filters_and_paginated_graph(monkeypatch):
    control = {"cve_id": "CVE-2024-0001", "published": "2024-01-02T00:00:00+00:00", "year": 2024,
               "severity": "CRITICAL", "description": "Fixture only", "cwes": ["CWE-79"]}
    stats = {"as_of": "2026-11-16T03:00:00+00:00", "total_cves": 1, "severity": {"CRITICAL": 1},
             "modified_last_30_days": 1, "unique_affected_products": 1, "cvss_by_version": {"3.1": {"average": 9.8, "count": 1}},
             "monthly": {"2024-01": 1}, "top_cwes": [["CWE-79", 1]], "top_vendors": [["vendor", 1]], "top_products": [["product", 1]]}
    edges = [{"relationship_key": str(i), "relationship": "REFERENCES" if i >= 507 else "AFFECTS",
              "entity": {"id": str(i)}} for i in range(559)]
    queries = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            path = urlsplit(self.path)
            query = {key: values[0] for key, values in parse_qs(path.query).items()}
            queries.append((path.path, query))
            status = 200
            if path.path == "/api/v1/kpis":
                body = stats
            elif path.path == "/api/v1/analytics/cassandra/snapshot":
                body = {"source": "cassandra", "snapshot": stats}
            elif path.path == "/ready":
                body = {"status": "ready"}
            elif path.path == "/api/v1/pipeline/status":
                body = {"status": "SUCCESS"}
            elif path.path == "/api/v1/vulnerabilities":
                identifier = query.get("cve_id")
                status = 422 if identifier and not re.fullmatch(r"CVE-\d{4}-\d{4,19}", identifier) else 200
                matches = not identifier or identifier == control["cve_id"]
                matches = matches and (not query.get("severity") or query["severity"] == control["severity"])
                body = {"total": int(matches), "items": [control] if matches else []}
            elif path.path.startswith("/api/v1/vulnerabilities/"):
                body = control
            elif path.path.startswith("/api/v1/graph/cve/"):
                page, size = int(query.get("page", 1)), int(query.get("page_size", 250))
                filtered = [edge for edge in edges if not query.get("relationship_type") or edge["relationship"] == query["relationship_type"]]
                more = page * size < len(filtered)
                body = {"items": filtered[(page - 1) * size:page * size], "page": page, "total": len(filtered),
                        "total_relationships": len(edges), "has_more": more, "next_page": page + 1 if more else None}
            else:
                status, body = 404, {}
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("API_URL", f"http://127.0.0.1:{server.server_port}")
    try:
        result = verify(f"http://127.0.0.1:{server.server_port}")
        assert result["status"] == "PASS", result
        assert all(case["status"] == "PASS" for case in result["cases"])
        assert any(query.get("page") == "3" for path, query in queries if "/graph/" in path)
        assert any({"cve_id", "year", "severity", "cwe", "published_from", "published_to"} <= query.keys() for path, query in queries)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
