"""External HTTPS OAuth Code+PKCE and six MCP calls. Never writes/prints tokens."""

import asyncio
import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from cloud_test_credentials import load
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE = "https://ti-136-114-21-18.sslip.io"
ISSUER = BASE + "/auth/realms/ti"
CALLBACK = "https://localhost/callback"


class Form(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.action = attrs.get("action")
        if tag == "input" and attrs.get("type") == "hidden" and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value", "")


def authorize(credentials):
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    with httpx.Client(timeout=45, follow_redirects=False) as client:
        metadata = client.get(ISSUER + "/.well-known/openid-configuration").json()
        assert metadata["issuer"] == ISSUER and "S256" in metadata["code_challenge_methods_supported"]
        response = client.get(metadata["authorization_endpoint"], params={"client_id": "ti-chatgpt", "response_type": "code", "redirect_uri": CALLBACK, "scope": "openid ti:read", "code_challenge": challenge, "code_challenge_method": "S256", "state": state, "resource": BASE + "/mcp"})
        logged_in = False
        for _ in range(10):
            location = response.headers.get("location", "")
            if location.startswith(CALLBACK):
                query = parse_qs(urlparse(location).query)
                assert query.get("state") == [state]
                if "code" not in query:
                    raise RuntimeError("OAuth authorization did not return a code")
                code = query["code"][0]
                break
            if location:
                target = urljoin(str(response.url), location)
                if not target.startswith(BASE + "/auth/"):
                    raise RuntimeError("Unexpected OAuth redirect origin")
                response = client.get(target)
                continue
            assert response.status_code == 200, "OAuth login endpoint not ready"
            form = Form()
            form.feed(response.text)
            if not form.action:
                raise RuntimeError("OAuth login/consent form unavailable")
            target = urljoin(str(response.url), form.action)
            if not target.startswith(BASE + "/auth/"):
                raise RuntimeError("Unexpected OAuth form origin")
            if not logged_in:
                form.fields.update(username="ti-owner", password=credentials["keycloak-user-password"])
                logged_in = True
            else:
                form.fields["accept"] = "Yes"
            response = client.post(target, data=form.fields)
        else:
            raise RuntimeError("OAuth flow did not complete within ten steps")
        data = {"grant_type": "authorization_code", "client_id": "ti-chatgpt", "client_secret": credentials["mcp-oauth-client-secret"], "code": code, "redirect_uri": CALLBACK, "code_verifier": verifier, "resource": BASE + "/mcp"}
        response = client.post(metadata["token_endpoint"], data=data)
        if response.status_code != 200:
            raise RuntimeError("OAuth code exchange rejected; response body suppressed")
        tokens = response.json()
        assert tokens["token_type"].lower() == "bearer"
        assert "ti:read" in tokens["scope"].split()
        replay = client.post(metadata["token_endpoint"], data=data)
        assert replay.status_code == 400 and replay.json()["error"] == "invalid_grant"
        return tokens["access_token"]


async def main():
    token = authorize(load())
    checks = {"oauth_authorization_code_pkce_s256": "PASS", "explicit_owner_login_consent": "PASS", "authorization_code_replay_rejected": "PASS"}
    async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=60) as client, streamable_http_client(BASE + "/mcp", http_client=client) as streams, ClientSession(streams[0], streams[1]) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        assert len(tools) == 6
        assert all(t.annotations and t.annotations.readOnlyHint and not t.annotations.destructiveHint for t in tools)
        checks["six_readonly_tools"] = "PASS"
        found = await session.call_tool("search_vulnerabilities", {"page_size": 1})
        assert not found.isError
        identifier = json.loads(found.content[0].text)["items"][0]["cve_id"]
        checks["search_vulnerabilities"] = "PASS"
        for name, args in (("get_cve_details", {"cve_id": identifier}), ("get_top_cwes", {}), ("get_vulnerability_statistics", {}), ("get_affected_products", {}), ("explore_cve_relationships", {"cve_id": identifier})):
            response = await session.call_tool(name, args)
            assert not response.isError, name
            json.loads(response.content[0].text)
            checks[name] = "PASS"
        invalid = await session.call_tool("get_cve_details", {"cve_id": "../../secrets"})
        assert invalid.isError
        checks["invalid_identifier_rejected"] = "PASS"
    result = {"at": datetime.now(UTC).isoformat(), "url": BASE + "/mcp", "issuer": ISSUER, "transport": "streamable-http", "checks": checks, "chatgpt_account_connected": False}
    Path("docs/evidence/gcp_mcp_protocol_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(main())
