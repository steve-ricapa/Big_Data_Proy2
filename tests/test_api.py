from fastapi.testclient import TestClient

from services.api.app import app


def test_liveness_and_input_validation():
    # No lifespan/database: these checks exercise HTTP routing and validation only.
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/vulnerabilities?page=0").status_code == 422
    assert client.get("/api/v1/vulnerabilities?severity=invalid").status_code == 422
    assert client.get("/api/v1/vulnerabilities?cwe=invalid").status_code == 422


def test_calendar_dates_and_date_range_are_validated():
    client = TestClient(app)
    assert client.get("/api/v1/vulnerabilities?published_from=2026-02-30").status_code == 422
    assert client.get("/api/v1/vulnerabilities?published_from=2026-03-01&published_to=2026-01-01").status_code == 422
    assert client.get("/api/v1/vulnerabilities?q=%20%20").status_code == 422
    assert client.get("/api/v1/vulnerabilities?q=" + "a" * 201).status_code == 422
    assert client.get("/api/v1/vulnerabilities/not-a-cve").status_code == 422
    assert client.get("/api/v1/graph/cve/not-a-cve").status_code == 422


def test_empty_count_uses_identity_index():
    from types import SimpleNamespace

    class Cursor:
        def __getattr__(self, name):
            return lambda *args: self

        def __iter__(self):
            return iter([])

    class Collection:
        def find(self, *args):
            return Cursor()

        def count_documents(self, query, **options):
            assert query == {}
            assert options["hint"] == "cve_id_1"
            return 0

    app.state.mongo = SimpleNamespace(collection=Collection())
    try:
        assert TestClient(app).get("/api/v1/vulnerabilities").json()["total"] == 0
    finally:
        del app.state.mongo


def test_search_combines_native_text_exact_identity_and_severity():
    from types import SimpleNamespace

    seen = []

    class Cursor:
        def __getattr__(self, name):
            return lambda *args: self

        def __iter__(self):
            return iter([{"cve_id": "CVE-2021-44228"}])

    class Collection:
        def find(self, query, projection):
            seen.append(query)
            assert projection["raw_cve"] == 0
            return Cursor()

        def count_documents(self, query, **options):
            assert "hint" not in options
            seen.append(query)
            return 1

    app.state.mongo = SimpleNamespace(collection=Collection())
    try:
        result = TestClient(app).get("/api/v1/vulnerabilities", params={"q": " log4j ", "severity": "CRITICAL", "cve_id": "CVE-2021-44228"})
        assert result.status_code == 200 and result.json()["total"] == 1
        assert seen == [{"cve_id": "CVE-2021-44228", "severity": "CRITICAL", "$text": {"$search": "log4j"}}] * 2
    finally:
        del app.state.mongo


def test_per_cve_products_and_missing_record():
    from types import SimpleNamespace

    row = {"cve_id": "CVE-2021-44228", "products": [{"vendor": "apache", "product": "log4j"}], "cpes": []}
    app.state.mongo = SimpleNamespace(collection=SimpleNamespace(find_one=lambda *args: row))
    try:
        client = TestClient(app)
        response = client.get("/api/v1/vulnerabilities/CVE-2021-44228/products")
        assert response.status_code == 200
        assert response.json()["items"] == row["products"]
        app.state.mongo.collection.find_one = lambda *args: None
        assert client.get("/api/v1/vulnerabilities/CVE-2021-44228/products").status_code == 404
        assert client.get("/api/v1/vulnerabilities/CVE-2021-44228").status_code == 404
    finally:
        del app.state.mongo


def test_graph_prioritizes_products_and_declares_truncation():
    from types import SimpleNamespace

    def query(text, **params):
        assert params["id"] == "CVE-2021-44228" and params["relationship_type"] is None
        if "count(r)" in text:
            return [{"n": 600, "filtered": 600}]
        assert "CASE type(r) WHEN 'AFFECTS' THEN 0" in text
        assert params["skip"] == 0 and params["size"] == 250
        return [{"cve_id": params["id"], "relationship": "AFFECTS", "entity": {"id": "log4j"}}]

    app.state.graph = SimpleNamespace(query=query)
    app.state.mongo = SimpleNamespace(collection=SimpleNamespace(find_one=lambda *args: {"raw_cve": {}}))
    try:
        result = TestClient(app).get("/api/v1/graph/cve/CVE-2021-44228")
        assert result.status_code == 200
        assert result.json()["truncated"] is True
        assert result.json()["total_relationships"] == 600
    finally:
        del app.state.graph
        del app.state.mongo
