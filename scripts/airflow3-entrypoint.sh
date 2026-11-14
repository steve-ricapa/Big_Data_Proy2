#!/usr/bin/env bash
set -euo pipefail
# SimpleAuthManager opens its password file in a+ even when credentials exist.
# Materialize the Docker secret on a private persistent volume, never in logs.
if [ ! -f /opt/airflow/auth/passwords.json ]; then
  umask 077
  cp /run/secrets/airflow3_passwords /opt/airflow/auth/passwords.json
fi
chmod 600 /opt/airflow/auth/passwords.json
exec /entrypoint "$@"
