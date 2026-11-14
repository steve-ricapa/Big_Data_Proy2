# Threat Intelligence Platform · Big Data II

Análisis de vulnerabilidades NIST NVD con **MongoDB, Apache Cassandra, Neo4j, Airflow, FastAPI y Streamlit**. Entrega académica: 16/11/2026. CVE publicado no equivale a ataque confirmado.

## Estado verificable

> **Runtime recomendado: Airflow 3.4.0** con dependencias mínimas bloqueadas:
> auditoría Python de 145 paquetes, 0 hallazgos conocidos. Migración local con
> siete tareas y retry real verificados; metadata 2.11 preservada y detenida.
> No es certificación de seguridad ni autorización para producción/GCP.
> [Migración](docs/implementation/airflow3-migration.md),
> [seguridad](docs/implementation/security_review.md).

**Cierre v2: 55 pruebas cloud PASS**, incluidas ocho integraciones de motores
y permisos; Windows **47 PASS/8 SKIP**, sin sumar ambas suites.
CRUD cloud: 12 operaciones temporales PASS con limpieza verificada. Corte
auditado 11/11 00:38 UTC: **174607 CVE únicos por motor**, cero duplicados y
misma huella; la sincronización diaria puede avanzar el siguiente corte.
Resultados finales, restauraciones y límites de reconstrucción:
[`final_acceptance_v2.md`](docs/report/final_acceptance_v2.md).
171791 era la carga inicial local/cloud; las suites37/42/53 son históricas,
no los resultados nuevos del cierre.

Matriz de 17 criterios académicos con evidencia trazable; porcentaje final en
el cierre v2, no equivale a producción. **GCP desplegado el 10-11/11/2026**
(una VM, USD ~4/día estimado; ver sección Terraform/GCP):
HTTPS+TLS1.3, OIDC Keycloak real, MCP remoto de seis herramientas solo
lectura, sincronización NVD diaria automática verificada con CVE reales
(174734 por motor en paridad al cierre v2), respaldo frío coordinado y restauración
aislada verificada. ChatGPT requiere login manual del dueño (documentado).
Terraform aplicado tras gate de costo; plan final sin deriva. Carga completa
previa por CLI compartida, conteos/huellas y originales nuevamente verificados.
El replay full Airflow3 `full34_20261110T170841` pasó las siete etapas sobre
los tres feeds, sin duplicar.

## Problema y objetivos

Integrar documentos NVD semiestructurados y representarlos con tres modelos complementarios; actualizar por CVE sin duplicación; responder consultas de severidad, tiempo, CWE y producto; mostrar KPI con reglas explícitas. No es un scanner, detector de ataques o inventario real de activos empresariales.

Arquitectura: [sistema](docs/architecture/system.md), [flujo](docs/architecture/data_flow.md), modelos [MongoDB](docs/data_models/mongodb.md), [Cassandra](docs/data_models/cassandra.md), [Neo4j](docs/data_models/neo4j.md), [KPI](docs/kpis/catalog.md).

## Instalación en Windows PowerShell

Requisitos: Docker Desktop Linux containers (~8GiB disponibles para Docker), Python 3.11 (no usar Python predeterminado 3.14 para drivers), `uv`, espacio libre ≥15GB. No se incluye dataset en imágenes ni Git.

```powershell
Set-Location C:\Users\steve\Desktop\Big_Data2
uv sync --locked --extra dev --extra mcp --python 3.11
.\.venv\Scripts\python.exe scripts/prepare_local.py
powershell -File scripts/start-local.ps1 -WithAirflow
```

Sin `-WithAirflow` solo inicia motores y web; con el flag inicia Airflow 3.4
mediante el overlay, en 18081. Usuarios Mongo read/readWrite se inicializan sin
resetear contraseñas existentes. No usar el airflow-init 2.11 del Compose raíz
para nuevas demostraciones. Secretos privados en `secrets/`; login Airflow
admin, contraseña `secrets/airflow-admin-password`, nunca capturar/publicar.

## Pipeline y demostración

**Ejecutar un pipeline a la vez** (CLI o Airflow). Los comandos siguientes son alternativas secuenciales, no lanzarlos en paralelo.

```powershell
# Inventario streaming y hashes (no vuelve a descargar)
docker compose run --rm --no-deps runner inventory --output docs/evidence/inventory.json
# Muestra; todas las bases deben estar saludables
docker compose run --rm --no-deps runner run --limit 1000 --run-dir data/staging/demo1000
# Completo, sin límite: puede tomar varios minutos
docker compose run --rm --no-deps runner run --run-dir data/staging/full_demo
# Reintento por motor sin repetir extracción
docker compose run --rm --no-deps runner cassandra --run-dir data/staging/full_demo
# Verificar identidad/hash además de conteos
docker compose run --rm --no-deps runner verify --run-dir data/staging/full_demo
# CRUD y regresión incremental real; IDs sintéticos aislados, se limpian
docker compose run --rm --no-deps runner crud --output docs/evidence/crud.json
docker compose run --rm --no-deps runner selftest --output docs/evidence/incremental.json
# Airflow 3: scheduler real, 10000 entradas y retry; pausa al finalizar
docker compose -f docker-compose.yml -f docker-compose.airflow3.yml exec -T airflow3-scheduler python /opt/project/scripts/verify_scheduler3.py
# Replay completo ya verificado; reservar tiempo, no lanzarlo durante la exposición:
# mismo comando anterior añadiendo --limit 0
```

Actualización incremental de un feed nuevo: `runner run --source /app/data/raw/nvd/modified/nvdcve-2.0-modified.json --run-dir data/staging/modified`. El operador coloca el feed local; descarga automática de NVD no implementada. DAG diario a 03:00 UTC, inicialmente pausado; habilitarlo en UI solo sin otra carga activa. Backfill relee el snapshot disponible, no reconstruye datos históricos ausentes.

## Dashboard y API

```powershell
docker compose --profile web up -d --wait api dashboard --wait-timeout 180
.\.venv\Scripts\python.exe scripts/verify_http.py
```

- Dashboard: **http://127.0.0.1:18501** — Overview, Explorer, Threat Analytics, Graph Intelligence, Data Pipeline.
- API/OpenAPI: **http://127.0.0.1:18000/docs** — KPI, búsqueda paginada, detalle CVE, rankings, subgrafo, estado.
- Airflow 3: **http://127.0.0.1:18081** — DAG `nvd_threat_intelligence`.

Solo puertos loopback de presentación; motores sin puertos publicados. API
Mongo read-only, ETL readWrite, admin solo bootstrap. Readiness comprueba los
tres motores; Threat Analytics consulta snapshot Cassandra real. Caché 30s,
botón actualizar, errores visibles. Aún no es un despliegue de producción TLS.

MCP opcional local: `docker compose build mcp`, luego
`uv run --extra mcp python scripts/verify_mcp.py`.
Configuración para agentes en [`services/mcp_server/README.md`](services/mcp_server/README.md).
No hay endpoint público ni integración ChatGPT remota afirmada.

## Datos

| Feed | Bytes | Entradas |
|---|---:|---:|
| 2024 |293745058|39369|
| 2025 |295852585|45482|
| 2026 |527484894|86940|
| Total |1117082537|171791|

[Inventario](docs/evidence/inventory.json), [caracterización](docs/dataset/inventory.md). El año del ID/feed no necesariamente es año de publicación. Originales inmutables en `data/raw/nvd/<año>/`. No se mezclan scores CVSS entre versiones; productos únicos no son registros CPE.

## Pruebas y calidad

```powershell
uv run pytest -q --junitxml=docs/evidence/unit_tests.xml
uv run ruff check src services tests airflow/dags scripts
# La Cassandra cloud autenticada se prueba con el lector de API, no pasando contraseñas a cqlsh.
```

Suite cloud de cierre: **55 PASS/0 FAIL/0 SKIP** (47 de código/contrato y ocho
integraciones de motores/permisos). Windows47 PASS/8 SKIP; no sumar
ejecuciones repetidas como tests distintos. Locks app/MCP y Airflow separados,
con hashes. [Resultados](docs/evidence/test_results.md),
[trazabilidad](docs/implementation/requirements.md).

```powershell
docker compose build tester
docker compose run --rm --no-deps tester -q -p no:cacheprovider --junitxml=docs/evidence/integration_tests.xml
docker compose run --rm --no-deps runner audit-kpis --output docs/evidence/kpi_audit.json
```

## Terraform / GCP

```powershell
$tf = "$env:LOCALAPPDATA\Temp\opencode\terraform\terraform.exe"
& $tf fmt -check -recursive infrastructure/terraform
& $tf -chdir=infrastructure/terraform/environments/dev init -backend=false -input=false
& $tf -chdir=infrastructure/terraform/environments/dev validate
& $tf -chdir=infrastructure/terraform/environments/dev plan -input=false -var='project_id=proyectobigdata2-514216' -var='boot_image=projects/debian-cloud/global/images/debian-12-bookworm-v20261109'
```

CLI temporal verificado SHA256; alternativamente instalar Terraform ≥1.13. ADC existente, no claves JSON (apply vía `scripts/terraform_adc.py`). **Prohibido apply/destroy, habilitar APIs, subir datos o crear recursos facturables sin aprobación explícita.** [Costos](docs/architecture/gcp_cost_estimate.md), [plan previo](docs/architecture/gcp-deployment-plan.md), [operación/TLS](docs/architecture/gcp-operations.md).

### Despliegue cloud real (10-11/2026, autorizado)

Desplegado y verificado E2E en una VM e2-standard-4 (us-central1-a):
13 contenedores, HTTPS `https://ti-136-114-21-18.sslip.io` (TLS 1.3, Basic
Auth), MCP remoto `…/mcp` con OIDC Keycloak PKCE S256, sincronización NVD
automática diaria 03:00 UTC (verificada con CVE reales, watermark tras
paridad), respaldo frío 02:00 UTC con subida privada a GCS y restauración
aislada verificada, 5 políticas de observabilidad, imágenes en Artifact
Registry, unidad `ti-stack.service` en arranque. Cierre v2: **174734 CVE por
motor** con paridad. Objetivo USD 5/día (estimado 4.08 con SKU oficiales).
Acceso operativo por IAP SSH; Airflow UI solo por túnel (18081).
Pendiente externo: conexión manual de la cuenta ChatGPT del dueño
([pasos](docs/evidence/gcp_mcp_validation.md)) y alertas presupuestarias
(bloqueadas por IAM de facturación). Detalle:
[entrega final](docs/report/final_delivery.md),
[arquitectura desplegada](docs/architecture/gcp_deployed_architecture.md),
[bitácora](docs/evidence/gcp_deployment.md).

## Estructura y entregables

`src/threat_intelligence/`: ETL, normalización, adapters, checkpoints, KPI y CLI. `airflow/dags/`: DAG delgado. `services/`: API y dashboard. `tests/`: pruebas. `scripts/`: operación. `infrastructure/`: Docker/Terraform. `data/`: originales/artefactos no versionables. `docs/`: arquitectura, modelos, [informe](docs/report/technical_report.md), [guion 24 minutos](docs/report/demo_script.md), [capturas](docs/evidence/screenshot_checklist.md), [decisiones](docs/implementation/decisions.md). Directorios iniciales vacíos se conservan, no implican funcionalidades extra.

Checkpoints en `checkpoint_data`; SQLite temporal de dedup en disco contenedor
para evitar I/O aleatorio Windows. NDJSON/manifiestos en `data/staging/`.
No borrar checkpoints durante operación normal. API consulta Mongo, Cassandra
y Neo4j; no todos los motores en cada gráfico.

Apagar solo este proyecto sin eliminar datos: `powershell -File scripts/stop-local.ps1`.
No usar `down -v` ni `--remove-orphans`. Límites: sin HA/TLS productivo, sin
descarga automática NVD, sin ChatGPT remoto, sin transacción distribuida ni
garantías ante escritores externos concurrentes. GCP requiere autorización.
