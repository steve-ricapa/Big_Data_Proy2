"""Run in a private ephemeral app container with the admin secret mounted.

Keycloak26 basic scope supplies the required stable subject claim. Uses real
admin API, never exposes bearer tokens or admin credentials in output/argv.
"""

import json
from pathlib import Path

import httpx

base = "http://keycloak:8080/auth"
with httpx.Client(timeout=30) as client:
    response = client.post(base + "/realms/master/protocol/openid-connect/token", data={"grant_type": "password", "client_id": "admin-cli", "username": "ti-admin", "password": Path("/run/secrets/keycloak_admin_password").read_text().strip()})
    if response.status_code != 200:
        raise RuntimeError("Private Keycloak admin authentication failed")
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    clients = client.get(base + "/admin/realms/ti/clients", params={"clientId": "ti-chatgpt"}).json()
    assert len(clients) == 1
    scopes = client.get(base + "/admin/realms/ti/client-scopes").json()
    basic = next((scope for scope in scopes if scope["name"] == "basic"), None)
    if basic:
        response = client.put(base + "/admin/realms/ti/clients/" + clients[0]["id"] + "/default-client-scopes/" + basic["id"])
        assert response.status_code == 204
    else:
        # Realm import may not create Keycloak's default scopes. Use its built-in
        # subject mapper on the registered client, not a fabricated user claim.
        url = base + "/admin/realms/ti/clients/" + clients[0]["id"] + "/protocol-mappers/models"
        existing = client.get(url).json()
        if not any(mapper["name"] == "subject" for mapper in existing):
            response = client.post(url, json={"name": "subject", "protocol": "openid-connect", "protocolMapper": "oidc-sub-mapper", "config": {"access.token.claim": "true", "introspection.token.claim": "true"}})
            assert response.status_code == 201
    print(json.dumps({"keycloak_subject_configuration": "PASS", "basic_scope_present": bool(basic)}))
