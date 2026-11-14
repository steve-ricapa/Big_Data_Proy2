"""Generate local-only secrets without printing their values or overwriting them."""

import base64
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
directory = root / "secrets"
directory.mkdir(exist_ok=True)


def secret(name, value):
    path = directory / name
    if not path.exists():
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)
    return path.read_text().strip()


mongo = secret("mongodb-root-password", secrets.token_urlsafe(32))
neo = secret("neo4j-password", secrets.token_urlsafe(32))
pg = secret("postgres-password", secrets.token_urlsafe(32))
secret("neo4j-auth", f"neo4j/{neo}")
secret("mongodb-uri", f"mongodb://ti_admin:{mongo}@mongodb:27017/?authSource=admin")
writer = secret("mongodb-writer-password", secrets.token_urlsafe(32))
reader = secret("mongodb-reader-password", secrets.token_urlsafe(32))
secret("mongodb-writer-uri", f"mongodb://ti_pipeline:{writer}@mongodb:27017/?authSource=threat_intelligence")
secret("mongodb-reader-uri", f"mongodb://ti_reader:{reader}@mongodb:27017/?authSource=threat_intelligence")
secret("airflow-db-uri", f"postgresql+psycopg2://airflow:{pg}@postgres/airflow")
secret("airflow-fernet-key", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
secret("airflow-web-key", secrets.token_urlsafe(32))
secret("airflow-admin-password", secrets.token_urlsafe(24))
print("Local secrets prepared; values were not displayed. Existing files preserved.")
