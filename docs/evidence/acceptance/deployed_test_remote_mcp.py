import importlib.util
import time

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("mcp") is None, reason="optional MCP extra")


@pytest.mark.parametrize("variant", ["valid", "wrong_scope", "expired", "wrong_audience", "wrong_issuer"])
def test_oidc_verifier_checks_signature_issuer_audience_expiry_scope(variant):
    import asyncio
    from types import SimpleNamespace

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from services.mcp_server.remote import OIDCVerifier

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = OIDCVerifier("https://ti.example/auth/realms/ti", "https://ti.example/jwks", "https://ti.example/mcp")
    verifier.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key()))
    claims = {"iss": verifier.issuer, "aud": verifier.audience, "sub": "owner", "iat": int(time.time()), "exp": int(time.time()) + 60, "scope": "ti:read", "azp": "ti-chatgpt"}
    if variant == "wrong_scope":
        claims["scope"] = "openid"
    if variant == "expired":
        claims["exp"] = int(time.time()) - 60
    if variant == "wrong_audience":
        claims["aud"] = "other-service"
    if variant == "wrong_issuer":
        claims["iss"] = "https://untrusted.example"
    token = jwt.encode(claims, key, algorithm="RS256")
    result = asyncio.run(verifier.verify_token(token))
    assert (result is not None) == (variant == "valid")


def test_remote_refuses_plain_http(monkeypatch):
    from services.mcp_server.remote import create_app

    monkeypatch.setenv("TI_PUBLIC_URL", "http://localhost:8080")
    with pytest.raises(ValueError, match="HTTPS"):
        create_app()
