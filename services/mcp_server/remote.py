"""Authenticated Streamable HTTP MCP; Keycloak owns OAuth/OIDC, not this app."""

import logging
import os
from functools import partial

import anyio
import jwt
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from services.mcp_server import server


class OIDCVerifier:
    def __init__(self, issuer, jwks_url, audience):
        self.issuer = issuer
        self.audience = audience
        self.jwks = jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=10)

    def decode(self, token):
        key = self.jwks.get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["RS256"], audience=self.audience, issuer=self.issuer, options={"require": ["exp", "iat", "sub", "iss", "aud"]}, leeway=10)

    async def verify_token(self, token):
        try:
            claims = await anyio.to_thread.run_sync(partial(self.decode, token))
        except (jwt.PyJWTError, ValueError, OSError) as error:
            logging.getLogger(__name__).warning("OIDC verification rejected: %s", type(error).__name__)
            return None
        scopes = claims.get("scope", "").split()
        if "ti:read" not in scopes:
            return None
        return AccessToken(token=token, client_id=claims.get("azp", ""), scopes=scopes, expires_at=claims["exp"], resource=self.audience, subject=claims["sub"])


def create_app():
    public = os.environ["TI_PUBLIC_URL"].rstrip("/")
    issuer = public + "/auth/realms/ti"
    resource = public + "/mcp"
    if not public.startswith("https://"):
        raise ValueError("Remote MCP requires an HTTPS public URL")
    from urllib.parse import urlparse

    hostname = urlparse(public).netloc
    verifier = OIDCVerifier(issuer, os.environ.get("TI_JWKS_URL", "http://keycloak:8080/auth/realms/ti/protocol/openid-connect/certs"), resource)
    remote = FastMCP(
        "Threat Intelligence NVD",
        tools=server.registered_tools(),
        token_verifier=verifier,
        auth=AuthSettings(issuer_url=issuer, resource_server_url=resource, required_scopes=["ti:read"], validate_token_resource=True),
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=[hostname, "localhost:*", "127.0.0.1:*"], allowed_origins=[public]),
    )
    @remote.custom_route("/health", methods=["GET"])
    async def health(request):
        return JSONResponse({"status": "ok", "transport": "streamable-http", "auth": "oidc"})

    return remote.streamable_http_app()
