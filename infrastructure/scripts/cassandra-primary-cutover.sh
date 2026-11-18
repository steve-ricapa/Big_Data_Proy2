#!/bin/bash
# Address change only: leaves the original host ID and Cassandra volume in place.
# Run once, after both peers were prepared but before either peer starts.
set -euo pipefail
[[ $# == 2 && $2 =~ ^[0-9a-f]{64}$ ]] || exit 2
bundle=$(realpath "$1")
cd /opt/threat-intelligence
primary=threat-intelligence-cassandra-1
scheduler=threat-intelligence-airflow3-scheduler-1
backup=$(find /srv/ti-data/cassandra-migration -mindepth 2 -maxdepth 2 -name result.json | sort | tail -1)
[[ -n "$backup" && ! -f secrets/cassandra-cluster.env ]]
python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r["restored"]["sha256_sum"] == sys.argv[2]; assert all(o["uploaded"] for o in r["objects"])' "$backup" "$2"
test "$(systemctl show ti-backup.service --property=ActiveState --value)" = inactive
test "$(docker exec "$primary" nodetool status | grep -Ec '^UN ')" = 1
before_id=$(docker exec "$primary" nodetool info | awk '/^ID /{print $3}')
rollback_dir=$(dirname "$backup")/original
mkdir -m 0700 "$rollback_dir"
tar -czf "$rollback_dir/code.tgz" scripts/cloud_backup.py scripts/backup_local.py src/threat_intelligence/common/config.py src/threat_intelligence/databases/cassandra/__init__.py
cp /etc/systemd/system/ti-stack.service "$rollback_dir/ti-stack.service"
docker exec "$scheduler" airflow dags pause nvd_threat_intelligence
guard=$'from airflow.models import DagRun\nfrom airflow.utils.session import create_session\nwith create_session() as s: assert s.query(DagRun).filter(DagRun.state.in_(("queued","running"))).count()==0'
rollback() {
    # Only valid until a peer joins. No production data is deleted or restored here.
    trap - ERR
    set +e
    if [[ -f secrets/cassandra-cluster.env ]]; then
        mv secrets/cassandra-cluster.env "$rollback_dir/failed.env"
    fi
    tar -xzf "$rollback_dir/code.tgz"
    bash scripts/cloud_compose.sh up -d --no-deps cassandra api airflow3-scheduler airflow3-api airflow3-dag-processor
    docker exec "$scheduler" airflow dags unpause nvd_threat_intelligence
}
trap rollback ERR
docker exec "$scheduler" python -c "$guard"
tar --no-same-owner -xzf "$bundle"
sed 's/TI_CASSANDRA_CONSISTENCY=LOCAL_QUORUM/TI_CASSANDRA_CONSISTENCY=LOCAL_ONE/; s/^TI_CASSANDRA_SEEDS=.*/TI_CASSANDRA_SEEDS=10.42.0.2/' infrastructure/cassandra/cluster.env.example > secrets/cassandra-cluster.env
bash scripts/cloud_compose.sh config --quiet
docker exec "$primary" nodetool drain
bash scripts/cloud_compose.sh up -d --no-deps --wait --wait-timeout 240 cassandra
after_id=$(docker exec "$primary" nodetool info | awk '/^ID /{print $3}')
test "$after_id" = "$before_id"
docker exec "$primary" nodetool status | grep -E '^UN +10[.]42[.]0[.]2 '
bash scripts/cloud_compose.sh up -d --no-deps --wait --wait-timeout 180 api airflow3-scheduler airflow3-api airflow3-dag-processor
curl --fail --silent --show-error http://127.0.0.1:18000/ready
trap - ERR
