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

## Reproducción desde un clon — cierre técnico 16/11/2026

El módulo `modules/secrets/main.tf` contiene solo recursos/IAM, no versiones ni
valores de secretos. Su exclusión Git accidental se corrige con una excepción
limitada a código. Los ocho módulos deben acompañar al clon; no usar archivos
locales ignorados para dar por válida una reconstrucción.

Desde la raíz del repositorio, con Terraform >=1.9,<2 instalado en PATH:

```powershell
terraform fmt -check -recursive infrastructure/terraform
terraform -chdir=infrastructure/terraform/environments/dev init -backend=false -lockfile=readonly -input=false
terraform -chdir=infrastructure/terraform/environments/dev validate
```

No se necesita copiar state, tfvars privados ni credenciales para validar.
La descarga del proveedor debe coincidir con `.terraform.lock.hcl` versionado.
No ejecutar `apply`, ni un plan contra producción sin los inputs/state privados
correctos. Un plan desde un clon sin state propondría crear recursos que ya
existen: **no es evidencia de deriva** ni autorización para duplicarlos.

La comprobación final se hace sobre un export de los archivos versionados en un
directorio temporal, con init/validate reales y sin copiar `.terraform` ni state.
Resultados precisos en `docs/audits/technical_deliverables_audit.md` desde raíz.
Esto acredita configuración reproducible y válida; no una VM reconstruida desde
cero ni reproducibilidad byte a byte de imágenes por tag.

## Despliegue y operación existentes (no ejecutar durante validación)

GCP fue desplegado con autorización el10–11/11/2026. El entorno dev permite
la VM, red/discos, IAM, buckets, Secret Manager, Artifact Registry y Monitoring.
Cloud Run queda deshabilitado por `web_services={}`; los servicios web corren
con Compose dentro de la VM, no como tres servicios Cloud Run.

Para reproducir un despliegue nuevo se necesita una aprobación independiente,
inputs como project_id/boot_image/IP/políticas, APIs e IAM habilitados, capacidad
y filesystem de disco preparados, bundle de aplicación y secretos privados.
`infrastructure/scripts/vm-bootstrap.sh` se niega a formatear automáticamente
discos y no inicia contenedores. `scripts/cloud_install.py` tiene operaciones
sensibles de instalación: inspeccionarlo antes de cualquier ejecución; no es
un comando de validación ni una herramienta para una VM existente con datos.

El runtime combina `docker-compose.yml`, `docker-compose.airflow3.yml`,
`docker-compose.secure.yml` y `docker-compose.public.yml` con
`secrets/public.env`. Sus valores no se incluyen en Git. Operación vigente y
límites: `docs/architecture/system.md`, `docs/architecture/gcp-operations.md`.
Las evidencias de planes previos son históricas, no un nuevo apply o plan de hoy.
