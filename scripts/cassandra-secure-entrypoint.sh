#!/usr/bin/env bash
set -euo pipefail
sed -i 's/^authenticator:.*/authenticator: PasswordAuthenticator/;s/^authorizer:.*/authorizer: CassandraAuthorizer/' /etc/cassandra/cassandra.yaml
exec /usr/local/bin/docker-entrypoint.sh "$@"
