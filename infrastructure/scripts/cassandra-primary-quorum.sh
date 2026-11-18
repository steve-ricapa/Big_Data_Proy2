#!/bin/bash
# Run only after the three nodes are UN. Resumable: does not drop schema/data.
set -euo pipefail
cd /opt/threat-intelligence
node=threat-intelligence-cassandra-1
test "$(docker exec "$node" nodetool status | grep -Ec '^UN +10[.]42[.]0[.](2|12|13) ')" = 3
docker run --rm --network host --entrypoint python \
    --mount "type=bind,source=$PWD/secrets/cassandra-admin-password,target=/run/secrets/admin,readonly" \
    --mount "type=bind,source=$PWD/scripts/cassandra_cluster_replication.py,target=/tmp/replication.py,readonly" \
    --user 50000:0 ti-app:local /tmp/replication.py
for keyspace in system_auth threat_intelligence; do
    docker exec "$node" nodetool repair --full --sequential "$keyspace"
done
docker exec "$node" nodetool netstats
install -m 0640 infrastructure/cassandra/cluster.env.example secrets/cassandra-cluster.env
bash scripts/cloud_compose.sh up -d --no-deps --wait --wait-timeout 180 api airflow3-api airflow3-scheduler airflow3-dag-processor
# Apply the second seed to node 1 without an avoidable restart: the compose
# declaration takes effect on its next controlled recreation.
curl --fail --silent --show-error http://127.0.0.1:18000/ready
install -m 0644 infrastructure/scripts/ti-stack.service /etc/systemd/system/ti-stack.service
systemctl daemon-reload
