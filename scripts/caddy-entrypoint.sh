#!/bin/sh
set -eu
export TI_WEB_PASSWORD_HASH="$(cat /run/secrets/web_password_hash)"
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
