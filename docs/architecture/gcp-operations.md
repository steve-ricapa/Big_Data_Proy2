# Operación GCP y Terraform (sin ejecución cloud)

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

## Checklist inicial: operador con autorización

- [ ] Confirmar proyecto existente, facturación/créditos, expiración y USD/PEN.
- [ ] Confirmar us-central1, zona y cuotas de VM, IP, discos, Run y Direct VPC.
- [ ] Revisar arquitectura, costos y ausencia de NAT/GKE/balanceador.
- [ ] Instalar Terraform >=1.9,<2; Docker Compose v2 para validación local.
- [ ] Aprobar identidad de despliegue: preferir impersonación, sin claves JSON.
- [ ] Habilitar **manualmente y con aprobación** las APIs necesarias:
  `compute.googleapis.com`, `iam.googleapis.com`, `iap.googleapis.com`,
  `oslogin.googleapis.com`, `storage.googleapis.com`, `secretmanager.googleapis.com`,
  `artifactregistry.googleapis.com`, `run.googleapis.com`, `logging.googleapis.com`,
  `monitoring.googleapis.com`. `serviceusage.googleapis.com` para administración;
  `iamcredentials.googleapis.com` si se usa impersonación. No requiere Cloud Build.
- [ ] Separar habilitador de APIs (`roles/serviceusage.serviceUsageAdmin`) del
  deployer; el código no contiene recursos de habilitación automática.
- [ ] Deployer con permisos de red/VM (`compute.networkAdmin`,
  `compute.securityAdmin`, `compute.instanceAdmin.v1`, permisos de discos),
  `iam.serviceAccountAdmin`, `iam.serviceAccountUser` solo sobre identidades
  adjuntadas, `storage.admin`, `secretmanager.admin`, `artifactregistry.admin`,
  `run.admin`, `monitoring.editor`, `logging.configWriter` y capacidad controlada
  de modificar IAM de proyecto para los bindings de telemetría.
  Son roles administrativos de despliegue, NO roles de runtime. En entorno real
  reemplazar por rol custom/etapas revisadas; no asignar Owner/Editor por comodidad.
- [ ] Operador: `iap.tunnelResourceAccessor`, `compute.osAdminLogin` para bootstrap
  (luego osLogin), permisos de lectura Compute y serviceAccountUser en SA de VM
  cuando lo exija OS Login. Usar condiciones IAP para destino/puerto 22.
- [ ] Uploader separado con objectCreator en raw, no dar escritura raw a la VM.
- [ ] Publisher con artifactregistry.writer en repositorio; runtime solo reader.
- [ ] Crear canales de notificación aprobados y presupuesto manual Billing.

No se han comprobado permisos en nube: esta lista requiere revisión del
administrador de la universidad y políticas de organización.

## Variables

Raíz Terraform ejecutable: `infrastructure/terraform/environments/dev/`.
El directorio superior agrupa módulos y entornos; no ejecutar plan allí.

| Variable | Configuración |
| --- | --- |
| `project_id` | ID real, proyecto existente con billing. |
| `region`, `zone` | Por defecto us-central1 / us-central1-a; mantener coherencia. |
| `prefix` | ti-dev; usar nombres cortos válidos para SA/buckets. |
| `subnet_cidr` | 10.42.0.0/24 sin solapamientos. |
| `boot_image` | ID exacto Debian 12 publicado y aprobado, no familia mutable. |
| `machine_type` | e2-standard-4 inicial. |
| `boot_disk_gb`, `data_disk_gb`, `disk_type` | 30,100,pd-balanced. |
| `allow_external_egress_ip` | false hasta aprobar egress o imagen preconstruida. |
| `deletion_protection` | true; cambiar con aprobación para retirar VM/Run. |
| `notification_channels` | IDs de canales existentes, opcionales. |
| `web_services` | Vacío inicialmente; mapa api/mcp/dashboard con image por digest,
  port, invokers, env no sensible, secret_env (ENV→nombre lógico), secret_version. |

No introducir credenciales en `env`, tfvars, startup-script, metadata o outputs.
Las variables `.env.example` de la raíz son para aplicaciones; Terraform no las
carga. Revisar las variables Terraform con `variables.tf` como fuente de verdad.

Secretos GCP: prefijo `ti-dev-` seguido de `mongodb-uri`,
`mongodb-root-password`, `cassandra-password`, `neo4j-password`,
`postgres-password`, `airflow-db-uri`, `airflow-fernet-key`, `airflow-web-key`,
`mcp-token`. El operador deberá añadir versiones fuera de Terraform, sin
mostrarlas en consola. Certificados/CA/keystores TLS también pendientes;
decidir su almacenamiento y ACL antes de conectar las bases.

VM puede acceder a esos secretos salvo mcp-token por IAM a nivel recurso.
Los servicios Run solo reciben los secretos solicitados en `secret_env`.
No se ha implementado el materializado seguro de secretos para Docker de VM:
preparar mecanismo runtime usando identidad adjunta, archivos root-only y
rotación antes de arrancar contenedores. No usar Terraform para ese propósito.

## Validación local y plan futuro (PowerShell)

En esta tarea Terraform no está instalado: `fmt/init/validate/plan` pendientes.
Docker Compose sí está disponible; `docker compose config --quiet` pasó sin
levantar servicios, descargar imágenes ni acceder a GCP. El bootstrap se revisó
con `bash -n` y pasó. No se verificaron imágenes
remotas ni motores en ejecución. No afirmar funcionalidad o seguridad TLS validada.

Comandos exactos desde PowerShell, **solo cuando tengamos acceso aprobado**:

```powershell
Set-Location 'C:\Users\steve\Desktop\Big_Data2\infrastructure\terraform\environments\dev'
Copy-Item terraform.tfvars.example terraform.tfvars
# EDITAR terraform.tfvars: proyecto, imagen exacta y decisiones aprobadas.
terraform fmt -recursive ..\..
terraform init -backend=false
terraform validate
# ADC previamente configurado por el operador, nunca enviar credenciales al agente.
terraform plan -var-file=terraform.tfvars -out=dev.tfplan
terraform show -no-color dev.tfplan
```

`plan` lee APIs y requiere acceso, pero no despliega. El ejemplo requiere
sustituir `boot_image`; no es un despliegue listo con valores ficticios.
No ejecutar `apply` sin nueva autorización explícita. Revisar que no aparezcan
APIs habilitadas, IAM público, puertos públicos, NAT o servicios inesperados.
Conservar lockfile para Windows y plataforma CI; no versionar state ni plan.
State local exige ACL y backup cifrado; preparar backend GCS privado y locking
antes de uso concurrente, fuera de este bootstrap y previa aprobación.

## Orden del despliegue futuro

1. Autorizar costos/egress, APIs, IAM y backend. Validar versiones/lock.
2. Revisar plan A con web_services vacío, sin publicar aplicaciones.
3. Solo después de autorización, provisionar; bootstrap se detiene si disco
   nuevo no tiene filesystem. Por IAP, comprobar disco y `lsblk`/`blkid` antes de
   formatear exclusivamente `/dev/disk/by-id/google-ti-data` como ext4. Esta
   operación es destructiva y requiere confirmación separada del operador.
4. Reejecutar bootstrap tras montar disco; verificar Docker y persistencia,
   revisar paquetes/versiones host. No asumir éxito automático del startup.
5. Resolver TLS, autenticación, usuarios mínimos, secretos runtime y overlay GCP
   siguiendo Docker README. Probar salud y CRUD antes de subir dataset.
6. Subir originales solo con autorización; verificar inventario SHA-256 GCS.
7. Implementar procesamiento y DAG real, pruebas de seis etapas/incrementales.
8. Construir imágenes reales, publicar en Registry y fijar digest; añadir
   web_services, env TLS y bindings invoker. Revisar un segundo plan.
9. Validar dashboard/tres bases, cinco KPIs, API/MCP autenticados y evidencias.

Acceso administrativo futuro (no ejecutado):

```powershell
gcloud compute ssh ti-dev-data --project=PROYECTO --zone=us-central1-a --tunnel-through-iap
# Acceso Airflow por túnel, nunca abrir 8080 en firewall:
gcloud compute ssh ti-dev-data --project=PROYECTO --zone=us-central1-a --tunnel-through-iap -- -L 8080:127.0.0.1:8080
```

## Retirada / destrucción (guía, NO ejecutada)

1. Detener DAGs y escrituras, exportar evidencias y verificar backups recuperables.
2. Revisar `terraform plan -destroy -var-file=terraform.tfvars`: el disco tiene
   `prevent_destroy=true`, VM/Run deletion_protection=true y buckets no permiten
   borrado no vacío. **Son barreras deliberadas**, no un error a eludir a ciegas.
3. Decidir retener o borrar disco. Para borrarlo, requiere edición revisada de
   su lifecycle; para conservarlo separar su gestión antes de destruir el resto.
   No retirar state como atajo sin registrar propiedad y costos residuales.
4. Tras nueva aprobación, desactivar deletion_protection mediante un cambio de
   configuración aplicado por operador; eliminar objetos solo con autorización
   explícita, considerar soft delete. Respaldar state antes de cambios.
5. Generar y revisar de nuevo plan de destrucción; ejecutar destrucción solo
   con autorización separada. No se proporciona un script de borrado automático.
6. Revisar discos, snapshots, buckets/objetos retenidos, Registry, versiones de
   secretos, Cloud Run, IPs y canales. Borrar secretos puede ser irreversible.
7. Verificar Billing al día siguiente: apagar VM no elimina discos ni buckets.
   APIs y proyecto existentes no se destruyen mediante este Terraform.
