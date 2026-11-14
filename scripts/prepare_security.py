"""Generate missing local/cloud security secrets privately, never reset existing."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "secrets"
root.mkdir(exist_ok=True)
for name in ("cassandra-admin-password", "cassandra-writer-password", "cassandra-reader-password", "web-password", "keycloak-admin-password", "keycloak-db-password", "keycloak-user-password", "mcp-oauth-client-secret"):
    path = root / name
    if not path.exists():
        path.write_text(secrets.token_urlsafe(36), encoding="utf-8")
        path.chmod(0o600)
print("Security secrets prepared without disclosure or replacement.")
