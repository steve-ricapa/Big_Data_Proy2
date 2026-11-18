#!/bin/bash
# Requires the project IAP operator, a paused DAG, and the staged probe files.
# Usage from the repo: bash scripts/test_cassandra_failover.sh 02
set -euo pipefail
[[ $# == 1 ]] || exit 2
case "$1" in
    02) zone=us-central1-b; ip=10.42.0.12; marker=during-node2-fault ;;
    03) zone=us-central1-c; ip=10.42.0.13; marker=during-node3-fault ;;
    *) exit 2 ;;
esac
py=${TI_PYTHON:-.venv/Scripts/python.exe}
peer() { gcloud compute ssh "ti-cassandra-$1" --zone="$zone" --project=proyectobigdata2-514216 --tunnel-through-iap --quiet --command="$2"; }
main() { "$py" scripts/gcp_remote.py --command "$1"; }
status() { main 'sudo docker exec threat-intelligence-cassandra-1 nodetool status threat_intelligence'; }
probe() { main "sudo docker exec -i threat-intelligence-airflow3-scheduler-1 python - $1 $2 < cassandra_cluster_probe.py"; }
app() { main 'python3 cassandra_cluster_http_probe.py'; }
wait_status() {
    local output
    for attempt in {1..12}; do
        output=$(status) || continue
        if [[ $(grep -c '^UN ' <<< "$output") == "$1" ]] && grep -Fq "$2" <<< "$output"; then
            date -u +%FT%TZ; echo "$output"; return 0
        fi
        sleep 5
    done
    return 1
}
wait_status 3 "UN  $ip"
app
probe write before-fault
recover() { peer "$1" 'sudo docker start ti-cassandra'; }
trap 'recover "$1"' EXIT
peer "$1" 'sudo docker stop --time 90 ti-cassandra'
wait_status 2 "DN  $ip"
probe write "$marker"
app
main 'sudo docker exec -i threat-intelligence-dashboard-1 python -c "import sys; __file__=\"/app/scripts/verify_dashboard_readonly.py\"; exec(compile(sys.stdin.read(),__file__,\"exec\"))" < verify_dashboard_readonly.py'
recover "$1"
trap - EXIT
wait_status 3 "UN  $ip"
probe read-all "$marker"
probe delete "$marker"
probe delete before-fault
