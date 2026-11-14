"""Local migration secrets, preserving original metadata and all existing secrets."""

import json
import secrets
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[1] / "secrets"
pg = (root / "postgres-password").read_text().strip()
admin = (root / "airflow-admin-password").read_text().strip()
values = {
    "airflow3-db-uri": f"postgresql+psycopg2://airflow3:{quote(pg, safe='')}@airflow3-postgres/airflow3",
    "airflow3-jwt": secrets.token_urlsafe(48),
    "airflow3-passwords": json.dumps({"admin": admin}),
}
for name, value in values.items():
    path = root / name
    if not path.exists():
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)
print("Airflow 3 local secret files prepared without disclosure or overwrites.")
