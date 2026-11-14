"""Create private Keycloak import/Caddy files for an explicitly supplied hostname."""

import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--hostname", required=True)
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,240}[a-z0-9]", args.hostname):
    parser.error("Expected a DNS hostname, not a URL")
root = Path(__file__).resolve().parents[1]
directory = root / "secrets"
public = "https://" + args.hostname


def secret(name):
    return (directory / name).read_text().strip()


realm = {
    "realm": "ti", "enabled": True, "sslRequired": "external",
    "registrationAllowed": False, "resetPasswordAllowed": False,
    "bruteForceProtected": True, "permanentLockout": False,
    "failureFactor": 5, "waitIncrementSeconds": 60, "maxFailureWaitSeconds": 900,
    "accessTokenLifespan": 600, "revokeRefreshToken": True, "refreshTokenMaxReuse": 0,
    "eventsEnabled": True, "eventsExpiration": 604800,
    "clientScopes": [{"name": "ti:read", "protocol": "openid-connect", "attributes": {"include.in.token.scope": "true", "display.on.consent.screen": "true", "consent.screen.text": "Read public NVD vulnerability data (no writes)"}, "protocolMappers": [{"name": "mcp-audience", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper", "config": {"included.custom.audience": public + "/mcp", "access.token.claim": "true", "id.token.claim": "false"}}, {"name": "subject", "protocol": "openid-connect", "protocolMapper": "oidc-sub-mapper", "config": {"access.token.claim": "true", "introspection.token.claim": "true"}}]}],
    "clients": [{
        "clientId": "ti-chatgpt", "name": "Threat Intelligence read-only MCP",
        "enabled": True, "publicClient": False, "secret": secret("mcp-oauth-client-secret"),
        "protocol": "openid-connect", "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False, "serviceAccountsEnabled": False,
        "implicitFlowEnabled": False, "consentRequired": True,
        "redirectUris": ["https://chatgpt.com/connector_platform_oauth_redirect", "https://chatgpt.com/connector/oauth/*", "https://localhost/callback"],
        "webOrigins": ["https://chatgpt.com"],
        "defaultClientScopes": ["ti:read"], "optionalClientScopes": ["offline_access"],
        "attributes": {"pkce.code.challenge.method": "S256", "oauth2.device.authorization.grant.enabled": "false", "backchannel.logout.session.required": "true"},
    }],
    "users": [{"username": "ti-owner", "enabled": True, "emailVerified": True, "firstName": "Project", "lastName": "Owner", "email": "owner@ti.invalid", "credentials": [{"type": "password", "value": secret("keycloak-user-password"), "temporary": False}]}],
}
path = directory / "keycloak-realm.json"
if path.exists() and json.loads(path.read_text()) != realm:
    raise RuntimeError("Realm import already exists with different settings; review instead of replacing")
path.write_text(json.dumps(realm, indent=2), encoding="utf-8")
path.chmod(0o600)
(directory / "public.env").write_text("TI_HOSTNAME=" + args.hostname + "\nTI_PUBLIC_URL=" + public + "\n", encoding="utf-8")
print("Private realm import and public hostname configuration prepared; no secrets displayed.")
