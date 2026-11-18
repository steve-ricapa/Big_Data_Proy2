#!/bin/bash
# COS boot hook. Never formats disks and never starts an unapproved empty node.
set -euo pipefail
device=/dev/disk/by-id/google-ti-cassandra-data
target=/mnt/disks/ti-cassandra
# COS defaults INPUT to DROP; narrow guest rules mirror the VPC rules.
allow() {
    iptables -w -C INPUT -p tcp -s "$1/32" --dport "$2" -j ACCEPT ||
        iptables -w -A INPUT -p tcp -s "$1/32" --dport "$2" -j ACCEPT
}
for peer in 10.42.0.2 10.42.0.12 10.42.0.13; do
    allow "$peer" 7000
done
allow 10.42.0.2 9042
mkdir -p "$target"
if [[ $(blkid -s TYPE -o value "$device" || true) != ext4 ]]; then
    echo 'Cassandra data disk not initialized; operator bootstrap required'
    exit 0
fi
mountpoint -q "$target" || mount -o discard,defaults "$device" "$target"
if [[ -e "$target/approved" ]]; then
    systemctl start docker
    docker start ti-cassandra
fi
