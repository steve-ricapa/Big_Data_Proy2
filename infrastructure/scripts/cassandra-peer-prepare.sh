#!/bin/bash
# Run as root on an explicitly provisioned COS replica. Does not start Cassandra.
set -euo pipefail
[[ $# -eq 2 ]] || { echo "usage: $0 IMAGE_ARCHIVE IMAGE_SHA256" >&2; exit 2; }
archive=$1 checksum=$2
[[ $checksum =~ ^[0-9a-f]{64}$ ]] || exit 2
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status
root=/mnt/disks/ti-cassandra
device=/dev/disk/by-id/google-ti-cassandra-data
meta() { curl -fsS -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
name=$(meta name)
ip=$(meta network-interfaces/0/ip)
case "$name,$ip,$(meta zone)" in
    ti-cassandra-02,10.42.0.12,*/us-central1-b) rack=us-central1-b; seeds=10.42.0.2 ;;
    ti-cassandra-03,10.42.0.13,*/us-central1-c) rack=us-central1-c; seeds=10.42.0.2,10.42.0.12 ;;
    *) echo 'Unexpected VM identity; refusing to touch any disk' >&2; exit 2 ;;
esac
[[ -b "$device" && $(blockdev --getsize64 "$device") -eq $((20 * 1024**3)) ]]
if [[ -z $(wipefs -n --noheadings --output TYPE "$device") ]]; then
    mkfs.ext4 -L ti-cassandra "$device"
fi
[[ $(blkid -s TYPE -o value "$device") == ext4 && $(blkid -s LABEL -o value "$device") == ti-cassandra ]]
mkdir -p "$root"
mountpoint -q "$root" || mount -o discard,defaults "$device" "$root"
[[ $(findmnt -no MAJ:MIN --target "$root") == $(lsblk -dn -o MAJ:MIN "$device") ]]
bash "$(dirname "$0")/cassandra-peer-startup.sh"
systemctl start docker
if docker container inspect ti-cassandra >/dev/null 2>&1; then
    echo 'Existing Cassandra container preserved; verify configuration before starting'
    exit 0
fi
mkdir -p "$root/data"
[[ -z $(find "$root/data" -mindepth 1 -print -quit) ]]
install -m 0755 "$(dirname "$0")/cassandra-secure-entrypoint.sh" "$root/secure-entrypoint.sh"
docker load -i "$archive"
docker create --name ti-cassandra --network host --restart unless-stopped \
    --memory 3g --log-opt max-size=10m --log-opt max-file=3 \
    --mount "type=bind,source=$root/data,target=/var/lib/cassandra" \
    --mount "type=bind,source=$root/secure-entrypoint.sh,target=/secure-entrypoint.sh,readonly" \
    --env CASSANDRA_CLUSTER_NAME=ti-dev-single-node --env CASSANDRA_NUM_TOKENS=16 \
    --env CASSANDRA_ENDPOINT_SNITCH=GossipingPropertyFileSnitch --env CASSANDRA_DC=dc1 \
    --env "CASSANDRA_RACK=$rack" --env "CASSANDRA_SEEDS=$seeds" \
    --env "CASSANDRA_LISTEN_ADDRESS=$ip" --env "CASSANDRA_BROADCAST_ADDRESS=$ip" \
    --env "CASSANDRA_RPC_ADDRESS=$ip" --env "CASSANDRA_BROADCAST_RPC_ADDRESS=$ip" \
    --env MAX_HEAP_SIZE=1024M --env HEAP_NEWSIZE=128M \
    --health-cmd 'nodetool statusbinary | grep -qx running' --health-start-period 180s \
    --health-interval 30s --health-timeout 20s --health-retries 8 \
    --entrypoint /bin/bash cassandra:4.1.9 /secure-entrypoint.sh cassandra -f
