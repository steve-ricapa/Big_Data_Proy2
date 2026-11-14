#!/usr/bin/env bash
# Ejecutado solo al desplegar una VM autorizada. No inicia contenedores.
set -euo pipefail
DISK=/dev/disk/by-id/google-ti-data
test -b "$DISK"
mkdir -p /srv/ti-data /opt/threat-intelligence
# No formatear automáticamente: evita destruir datos de un disco existente.
if ! blkid "$DISK" >/dev/null 2>&1; then
  echo 'Disco sin filesystem. Revisar y formatear manualmente antes de continuar.'
  exit 1
fi
UUID=$(blkid -s UUID -o value "$DISK")
grep -q "UUID=$UUID " /etc/fstab || echo "UUID=$UUID /srv/ti-data ext4 defaults,nofail 0 2" >> /etc/fstab
mountpoint -q /srv/ti-data || mount /srv/ti-data
# Requiere salida a Internet aprobada. Versionar imagen base de VM antes de producción.
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
echo 'Bootstrap completo. Configurar secretos, TLS y Compose antes de iniciar servicios.'
