#!/bin/bash
set -euo pipefail
cd /opt/threat-intelligence
options=(--env-file secrets/public.env -f docker-compose.yml -f docker-compose.airflow3.yml -f docker-compose.secure.yml -f docker-compose.public.yml)
if [[ -f secrets/cassandra-cluster.env ]]; then
    options+=(--env-file secrets/cassandra-cluster.env -f docker-compose.cassandra-cluster.yml)
fi
exec docker compose "${options[@]}" "$@"
