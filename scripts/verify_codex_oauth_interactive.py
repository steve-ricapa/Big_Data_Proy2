"""User-operated native OAuth validation; never automates or reads credentials.

Run from the project root with --interactive. The user signs in and consents
in their own browser. Codes, state, verifier and tokens stay in process memory.
Only allowlisted results are saved. This is NOT a Codex App E2E test.
"""
import argparse
import asyncio
import base64
import hashlib
import json
import secrets
import time
import webbrowser
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import jwt
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BASE = "https://ti-136-114-21-18.sslip.io"
ISSUER = BASE + "/auth/realms/ti"
RESOURCE = BASE + "/mcp"
CALLBACK = "http://127.0.0.1:43219/callback/GnTeVrGD9Hed"
OUTPUT = Path(__file__).resolve().parents[1] / "docs/evidence/codex_diagnosis/interactive_validation.json"
TOOLS = {
    "search_vulnerabilities", "get_cve_details", "get_top_cwes",
    "get_vulnerability_statistics", "get_affected_products", "explore_cve_relationships",
}


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true", required=True)
    parser.parse_args()
    evidence = {
        "at": datetime.now(UTC).isoformat(),
        "client": "ti-codex",
        "test_client": "Python OAuth + MCP SDK (not Codex App)",
        "status": "PENDING_USER_LOGIN",
        "codex_app_e2e": "PENDING",
        "checks": {},
    }
    stage = "discovery"
    try:
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            response = client.get(ISSUER + "/.well-known/openid-configuration")
            assert response.status_code == 200
            metadata = response.json()
            assert metadata["issuer"] == ISSUER
            for key, suffix in (("authorization_endpoint", "auth"), ("token_endpoint", "token"), ("jwks_uri", "certs")):
                assert metadata[key] == ISSUER + "/protocol/openid-connect/" + suffix
            evidence["checks"]["discovery"] = "PASS"
            stage = "interactive_login"
            state = secrets.token_urlsafe(32)
            verifier = secrets.token_urlsafe(64)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
            received = {}

            class CallbackHandler(BaseHTTPRequestHandler):
                def log_message(self, *_args):
                    pass  # Never log callback URLs, codes, state or request headers.

                def do_GET(self):
                    parts = urlsplit(self.path)
                    query = parse_qs(parts.query)
                    good = (
                        self.headers.get("Host") == "127.0.0.1:43219"
                        and parts.path == urlsplit(CALLBACK).path
                        and query.get("state") == [state]
                        and query.get("iss") == [ISSUER]
                    )
                    if good and len(query.get("code", [])) == 1:
                        received["code"] = query["code"][0]
                        status, message = 200, b"Login received. Return to the validation terminal."
                    elif good and query.get("error"):
                        received["error"] = True
                        status, message = 400, b"Authorization was not granted. Return to the terminal."
                    else:
                        status, message = 400, b"Invalid callback. No authorization code accepted."
                    self.send_response(status)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.end_headers()
                    self.wfile.write(message)

            params = {
                "client_id": "ti-codex", "redirect_uri": CALLBACK,
                "response_type": "code", "scope": "openid ti:read", "resource": RESOURCE,
                "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
            }
            with HTTPServer(("127.0.0.1", 43219), CallbackHandler) as server:
                server.timeout = 1
                print("Complete the ti-codex login and consent in your browser. No credentials are read by this script.")
                assert webbrowser.open(metadata["authorization_endpoint"] + "?" + urlencode(params)), "Browser unavailable"
                deadline = time.monotonic() + 300
                while not received and time.monotonic() < deadline:
                    server.handle_request()
            if "code" not in received:
                evidence["status"] = "PENDING_USER_LOGIN"
                evidence["stopped_at"] = "consent_denied_or_login_timeout"
                return evidence
            evidence["checks"]["manual_login_callback_state_issuer"] = "PASS"
            stage = "authorization_code_exchange"
            response = client.post(metadata["token_endpoint"], data={
                "grant_type": "authorization_code", "client_id": "ti-codex",
                "code": received.pop("code"), "redirect_uri": CALLBACK,
                "code_verifier": verifier, "resource": RESOURCE,
            })
            assert response.status_code == 200, "Code exchange failed; body suppressed"
            tokens = response.json()
            assert tokens.get("token_type", "").lower() == "bearer"
            assert tokens.get("refresh_token")
            evidence["checks"]["real_public_client_pkce_code_exchange"] = "PASS"
            stage = "signed_access_token_validation"
            jwks = jwt.PyJWKClient(metadata["jwks_uri"])

            def validate(token):
                key = jwks.get_signing_key_from_jwt(token)
                claims = jwt.decode(token, key.key, algorithms=["RS256"], audience=RESOURCE, issuer=ISSUER,
                                    options={"require": ["exp", "iat", "sub", "iss", "aud"]}, leeway=10)
                assert "ti:read" in claims.get("scope", "").split()
                assert claims.get("azp") == "ti-codex"
                return {k: claims[k] for k in ("iss", "aud", "scope", "azp")}

            evidence["issued_claims"] = validate(tokens["access_token"])
            evidence["checks"]["signed_jwt_issuer_audience_scope_subject_expiry"] = "PASS"
            stage = "refresh"
            response = client.post(metadata["token_endpoint"], data={
                "grant_type": "refresh_token", "client_id": "ti-codex",
                "refresh_token": tokens["refresh_token"], "resource": RESOURCE,
            })
            assert response.status_code == 200, "Refresh failed; body suppressed"
            renewed = response.json()
            validate(renewed["access_token"])
            assert renewed.get("refresh_token") and renewed["refresh_token"] != tokens["refresh_token"]
            evidence["checks"]["public_refresh_rotation_and_signed_validation"] = "PASS"
            stage = "authenticated_mcp"

            async def check_mcp():
                async with httpx.AsyncClient(headers={"Authorization": "Bearer " + renewed["access_token"]}, timeout=60) as http_client:  # noqa: SIM117 -- keep token-bearing context separate from SDK contexts
                    async with streamable_http_client(RESOURCE, http_client=http_client) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            init = await session.initialize()
                            evidence["protocol_version"] = init.protocolVersion
                            evidence["checks"]["authenticated_initialize"] = "PASS"
                            tools = (await session.list_tools()).tools
                            assert {tool.name for tool in tools} == TOOLS
                            evidence["checks"]["authenticated_tools_list_six"] = "PASS"
                            result = await session.call_tool("search_vulnerabilities", {"page_size": 1})
                            assert not result.isError
                            items = json.loads(result.content[0].text)["items"]
                            assert items
                            identifier = items[0]["cve_id"]
                            evidence["checks"]["tool_search_vulnerabilities"] = "PASS"
                            for name, arguments in (
                                ("get_cve_details", {"cve_id": identifier}), ("get_top_cwes", {}),
                                ("get_vulnerability_statistics", {}), ("get_affected_products", {}),
                                ("explore_cve_relationships", {"cve_id": identifier}),
                            ):
                                result = await session.call_tool(name, arguments)
                                assert not result.isError
                                evidence["checks"]["tool_" + name] = "PASS"

            asyncio.run(check_mcp())
            evidence["status"] = "PASS_AUTHENTICATED_TEST_CLIENT"
            print("Authenticated test-client checks passed. Codex App E2E remains PENDING.")
    except KeyboardInterrupt:
        evidence["status"] = "PENDING_USER_LOGIN"
        evidence["stopped_at"] = stage
    except Exception as exc:  # noqa: BLE001 -- suppress secret-bearing SDK/HTTP exception text at this boundary
        evidence["status"] = "FAIL"
        evidence["failed_stage"] = stage
        evidence["exception_type"] = type(exc).__name__  # No raw exception/response URLs.
        print("Validation failed at " + stage + ". Sensitive diagnostics suppressed.")
    finally:
        OUTPUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return evidence


if __name__ == "__main__":
    result = run()
    print("Evidence: " + str(OUTPUT))
    raise SystemExit(0 if result["status"] == "PASS_AUTHENTICATED_TEST_CLIENT" else 1)
