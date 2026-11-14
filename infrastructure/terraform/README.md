# Terraform

Punto de entrada: `environments/dev/`. Ejecutar desde allí, no desde esta carpeta.
Ocho módulos locales: networking, compute, storage, iam, secrets, registry,
cloud_run y observability. Las interfaces están declaradas en cada `main.tf`;
el ensamblaje dev representa exclusivamente el escenario A.

Proveedor heredado google 6.49.0 desde dev; no módulos remotos mutables ni
habilitación automática de APIs. Terraform >=1.9,<2.0. Los módulos solo usan
el proveedor hashicorp/google. Al disponer de Terraform, ejecutar init y
versionar su lockfile (no inventarlo ni editar checksums manualmente).

No hay backend remoto configurado: el state local no se debe compartir ni
subir a Git. Cambiar a backend privado aprobado antes de trabajo concurrente.
Plan de arquitectura y operación en `docs/architecture/` desde la raíz.

## Validaciones realizadas en esta tarea

### Estado vigente, segunda revisión 10/11/2026
- CLI temporal existente en `%LOCALAPPDATA%/Temp/opencode/terraform/terraform.exe`.
- `fmt -check`, `init -backend=false`, `validate` y `plan` correctos.
- Plan vigente: 37 altas, 0 cambios, 0 bajas, sin apply/destroy ni APIs habilitadas.
- Evidencias `docs/evidence/revalidation_terraform_*` desde raíz. Lockfile real
  existente conservado. ADC disponible se utiliza sin leer/imprimir credenciales.
- Workloads locales sí construidos/probados; no infraestructura cloud ejecutada.

### Histórico de la preparación inicial (ya superado)

- `docker compose config --quiet`: correcto, sin iniciar Docker workloads.
- `bash -n infrastructure/scripts/vm-bootstrap.sh`: correcto.
- Rutas de ocho módulos y startup-script: existen.
- Fórmulas de costos: recalculadas con Python estándar.
- Los tres originales: bytes y SHA-256 coinciden con el inventario inicial.
- Terraform no disponible en PATH: no se ejecutaron fmt, init, validate o plan.
  No hay validación semántica del proveedor ni lockfile todavía.
- No se descargaron imágenes, probaron healthchecks, TLS, conectividad ni
  permisos en GCP. No se ejecutaron gcloud ni operaciones cloud.

Bloqueos antes de un despliegue funcional: boot_image real, APIs/IAM autorizados,
decisión de egress, inicialización controlada de filesystem, secretos runtime,
TLS/autenticación y overlay GCP, imágenes reales y compatibilidad de versiones.
El script bootstrap no inicia contenedores ni formatea automáticamente discos.
