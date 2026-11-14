import importlib.util

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="optional MCP extra not installed")


def test_mcp_sanitizes_connection_errors(monkeypatch):
    import httpx

    from services.mcp_server import server

    def fail(*args, **kwargs):
        raise httpx.ConnectError("sensitive-host-or-secret")

    monkeypatch.setattr(httpx, "get", fail)
    with pytest.raises(RuntimeError, match="API unavailable") as error:
        server.get_vulnerability_statistics()
    assert "sensitive" not in str(error.value)


def test_mcp_forwards_only_fixed_read_path(monkeypatch):
    from services.mcp_server import server

    def query(path, **params):
        assert path == "/api/v1/vulnerabilities"
        assert params == {"cve_id": "CVE-2024-1000", "page": 2, "page_size": 10, "include_metadata": True}
        return {"items": []}

    monkeypatch.setattr(server, "query", query)
    assert server.search_vulnerabilities("CVE-2024-1000", page=2, page_size=10) == {"items": []}


def test_mcp_forwards_keyword_severity_and_exact_products(monkeypatch):
    from services.mcp_server import server

    calls = []
    monkeypatch.setattr(server, "query", lambda path, **params: calls.append((path, params)) or {"items": []})
    server.search_vulnerabilities("CVE-2021-44228", keyword="log4j", severity="CRITICAL")
    server.get_affected_products("CVE-2021-44228")
    server.get_affected_products()
    assert calls == [
        ("/api/v1/vulnerabilities", {"page": 1, "page_size": 25, "cve_id": "CVE-2021-44228", "q": "log4j", "severity": "CRITICAL", "include_metadata": True}),
        ("/api/v1/vulnerabilities/CVE-2021-44228/products", {"include_metadata": True, "page": 1, "view": "legacy"}),
        ("/api/v1/products/top", {"include_metadata": True, "page": 1, "view": "legacy", "mode": "ranking"}),
    ]


@pytest.mark.parametrize("status,label", [(404, "not found"), (422, "parameters"), (401, "authentication"), (503, "unavailable")])
def test_mcp_distinguishes_http_failures_without_body_or_credentials(monkeypatch, status, label):
    import httpx

    from services.mcp_server import server

    response = httpx.Response(status, text="sensitive-upstream-detail", request=httpx.Request("GET", "http://private-host/"))
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: response)
    with pytest.raises(RuntimeError, match=label) as error:
        server.get_cve_details("CVE-2021-44228")
    assert "sensitive" not in str(error.value)
    assert "private-host" not in str(error.value)
