"""Executed inside Airflow; reads a Docker secret, never logs the password."""

from pathlib import Path

from airflow.www.app import create_app

app = create_app()
with app.app_context():
    manager = app.appbuilder.sm
    if manager.find_user(username="admin") is None:
        user = manager.add_user(
            username="admin",
            first_name="Big",
            last_name="Data",
            email="admin@localhost.invalid",
            role=manager.find_role("Admin"),
            password=Path("/run/secrets/airflow_admin_password").read_text().strip(),
        )
        if not user:
            raise RuntimeError("Admin creation failed")
print("Airflow admin prepared without displaying credentials.")
