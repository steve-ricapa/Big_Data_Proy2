# Threat Intelligence Platform · Big Data II

Análisis de vulnerabilidades NIST NVD con **MongoDB, Apache Cassandra, Neo4j, Airflow, FastAPI y Streamlit**. Entrega académica: 16/11/2026. CVE publicado no equivale a ataque confirmado.

## Estado verificable — 16/11/2026

Runtime recomendado: **Python 3.11 y Airflow 3.4.0**, con locks separados.
La referencia Airflow 2.11 se conserva como histórico, no para instalaciones
nuevas. [Migración](docs/implementation/airflow3-migration.md).

- GCP desplegado: una VM, tres motores reales, FastAPI, Streamlit, Caddy HTTPS
  y MCP remoto con Keycloak/OIDC. No es un servicio HA ni una certificación de seguridad.
- Corte de datos comprobado: **176803 CVE por motor**, sin duplicados y con
  huella coincidente; KPI del **16/11 a las03:01:29 UTC**. Las ingestas futuras
  pueden cambiar estos valores legítimamente.
- DAG de siete tareas, sincronización NVD automática diaria03:00 UTC, backup
  coordinado02:00 UTC. Las seis ejecuciones diarias11–16/11 fueron SUCCESS.
- **Codex App: validación exitosa confirmada manualmente por el dueño** durante
  el cierre técnico. No equivale a una nueva suite automatizada OAuth ejecutada
  por el agente. No se cambian OAuth/Keycloak para repetir esa validación.
- Resultados actuales y límites: [auditoría técnica](docs/audits/technical_deliverables_audit.md).
  Las suites47/55, CRUD y restores del11/11 en
  [cierre v2](docs/report/final_acceptance_v2.md) son evidencia histórica,
  no resultados nuevos ni cuentas que deban permanecer constantes.

La matriz de17 criterios en `docs/implementation/requirements.md` fue elaborada
por el proyecto; no se localizó una rúbrica original del profesor. Los171791
registros son la carga inicial de feeds, no el total actual.

## Problema y objetivos

Integrar documentos NVD semiestructurados y representarlos con tres modelos complementarios; actualizar por CVE sin duplicación; responder consultas de severidad, tiempo, CWE y producto; mostrar KPI con reglas explícitas. No es un scanner, detector de ataques o inventario real de activos empresariales.

Arquitectura: [sistema](docs/architecture/system.md), [flujo](docs/architecture/data_flow.md), modelos [MongoDB](docs/data_models/mongodb.md), [Cassandra](docs/data_models/cassandra.md), [Neo4j](docs/data_models/neo4j.md), [KPI](docs/kpis/catalog.md).

## Instalación en Windows PowerShell

Requisitos: Docker Desktop Linux containers (~8GiB disponibles para Docker), Python 3.11 (no usar Python predeterminado 3.14 para drivers), `uv`, espacio libre ≥15GB. No se incluye dataset en imágenes ni Git.

```powershell
git clone https://github.com/steve-ricapa/Big_Data_Proy2.git
Set-Location Big_Data_Proy2
uv sync --locked --extra dev --extra mcp --python 3.11
.\.venv\Scripts\python.exe scripts/prepare_local.py
powershell -File scripts/start-local.ps1 -WithAirflow
```

Sin `-WithAirflow` solo inicia motores y web; con el flag inicia Airflow 3.4
mediante el overlay, en 18081. Usuarios Mongo read/readWrite se inicializan sin
resetear contraseñas existentes. No usar el airflow-init 2.11 del Compose raíz
para nuevas demostraciones. Secretos privados en `secrets/`; login Airflow
admin, contraseña `secrets/airflow-admin-password`, nunca capturar/publicar.
`start-local.ps1` construye primero `ti-app:local`; el dashboard usa la etiqueta
separada `ti-dashboard:local` mediante `infrastructure/docker/dashboard.Dockerfile`.
Así una actualización del dashboard no obliga a recrear API o MCP.

## Pipeline local y sincronización

**Ejecutar un pipeline a la vez** (CLI o Airflow). Los comandos siguientes
escriben en las bases: son alternativas operativas locales, no pruebas de solo
lectura ni instrucciones para repetir cargas en producción. Un clon nuevo no
incluye feeds ni datos; colocar los feeds NVD 2.0 en `data/raw/nvd/<año>/` para
un replay local, o usar `sync` para la ventana incremental reciente.

```powershell
$compose = @('compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.airflow3.yml', '-f', 'docker-compose.secure.yml')
# Inventario streaming local (no descarga)
docker @compose run --rm --no-deps runner inventory --output docs/evidence/inventory.json
# Muestra; todas las bases deben estar saludables
docker @compose run --rm --no-deps runner run --limit 1000 --run-dir data/staging/demo1000
# Completo, sin límite: puede tomar varios minutos
docker @compose run --rm --no-deps runner run --run-dir data/staging/full_demo
# Reintento por motor sin repetir extracción
docker @compose run --rm --no-deps runner cassandra --run-dir data/staging/full_demo
# Verificar identidad/hash además de conteos
docker @compose run --rm --no-deps runner verify --run-dir data/staging/full_demo
# CRUD y regresión incremental real; IDs sintéticos aislados, se limpian
docker @compose run --rm --no-deps runner crud --output docs/evidence/crud.json
docker @compose run --rm --no-deps runner selftest --output docs/evidence/incremental.json
# Airflow 3: scheduler real, 10000 entradas y retry; pausa al finalizar
docker @compose exec -T airflow3-scheduler python /opt/project/scripts/verify_scheduler3.py
# Replay completo ya verificado; reservar tiempo, no lanzarlo durante la exposición:
# mismo comando anterior añadiendo --limit 0
```

Actualización desde un archivo local: añadir `--source /app/data/raw/nvd/modified/nvdcve-2.0-modified.json`
a `runner run`. Para **descarga automática NVD** en una instalación local:
`docker @compose run --rm --no-deps runner sync --run-dir data/staging/sync_demo`.
Usa API NVD, páginas durables, solape2h y watermark confirmado solo tras paridad.
Sin watermark inicial consulta los dos días recientes: no rellena todo el histórico.
El DAG nuevo nace pausado; en el cloud existente está activo. Ejecuciones
programadas usan NVD; manuales `source_mode=auto` usan feeds locales.
Un backfill histórico masivo requiere aprobación separada.

## Dashboard y API

```powershell
# Después de start-local.ps1, que prepara usuarios y motores:
docker @compose --profile web up -d --wait api dashboard --wait-timeout 180
.\.venv\Scripts\python.exe scripts/verify_http.py
```

- Dashboard: **http://127.0.0.1:18501** — Overview, Explorer, Threat Analytics, Graph Intelligence, Data Pipeline.
- API/OpenAPI: **http://127.0.0.1:18000/docs** — KPI, búsqueda paginada, detalle CVE, rankings, subgrafo, estado.
- Airflow 3: **http://127.0.0.1:18081** — DAG `nvd_threat_intelligence`.

Solo puertos loopback de presentación; motores sin puertos publicados. API
Mongo read-only, ETL readWrite, admin solo bootstrap. Readiness comprueba los
tres motores; Threat Analytics consulta snapshot Cassandra real. Caché 30s,
botón actualizar y errores visibles. Estos endpoints loopback son del entorno
local; el cloud existente sí tiene HTTPS mediante Caddy.

MCP opcional local: `docker compose build mcp`, luego
`uv run --extra mcp python scripts/verify_mcp.py`.
Configuración para agentes en [`services/mcp_server/README.md`](services/mcp_server/README.md).
Endpoint público cloud: **https://ti-136-114-21-18.sslip.io/mcp**.
La confirmación manual vigente es de **Codex App**, no de una cuenta ChatGPT
distinta. [Contrato MCP](docs/integrations/mcp_comprehensive_remediation.md).
No ejecutar de nuevo la suite exhaustiva ni modificar identidad para abrir el dashboard.

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
uv run --extra dev --extra mcp pytest -q --junitxml=docs/evidence/unit_tests.xml
uv run --extra dev --extra mcp ruff check src services tests airflow/dags scripts
# La Cassandra cloud autenticada se prueba con el lector de API, no pasando contraseñas a cqlsh.
```

El conteo vigente de pruebas y lecturas cloud está en la auditoría técnica;
no sumar ejecuciones repetidas ni presentar SKIP como PASS. Locks app/MCP y
Airflow separados con hashes. La suite cloud55 y Windows47 del cierre v2
son históricas. Los comandos siguientes **sí escriben CRUD temporal**: solo
usarlos en un entorno aislado autorizado, no como auditoría productiva de lectura.

```powershell
docker @compose build tester
docker @compose run --rm --no-deps tester -q -p no:cacheprovider --junitxml=docs/evidence/integration_tests.xml
```

## Terraform / GCP

```powershell
# Terraform instalado en PATH; alternativamente indicar su ruta absoluta.
terraform fmt -check -recursive infrastructure/terraform
terraform -chdir=infrastructure/terraform/environments/dev init -backend=false -lockfile=readonly -input=false
terraform -chdir=infrastructure/terraform/environments/dev validate
```

Instalar Terraform compatible con `versions.tf` y conservar el lockfile. Estos
comandos no requieren state productivo ni aplican cambios. Los ocho módulos
locales, incluido `modules/secrets`, forman parte del código; los secretos,
state y tfvars privados no. [Reproducción y despliegue](infrastructure/terraform/README.md).
La sintaxis validada no demuestra una reconstrucción de VM vacía ni deriva
cero. **Prohibido apply/destroy, habilitar APIs o crear recursos facturables sin
aprobación explícita.** [Costos](docs/architecture/gcp_cost_estimate.md),
[operación/TLS](docs/architecture/gcp-operations.md).

### Despliegue cloud real (10-11/2026, autorizado)

Desplegado y verificado E2E en una VM e2-standard-4 (us-central1-a):
13 contenedores, HTTPS `https://ti-136-114-21-18.sslip.io` (TLS 1.3, Basic
Auth), MCP remoto `…/mcp` con OIDC Keycloak PKCE S256, sincronización NVD
automática diaria 03:00 UTC (verificada con CVE reales, watermark tras
paridad), respaldo frío 02:00 UTC con subida privada a GCS y restauración
aislada verificada, 5 políticas de observabilidad, imágenes en Artifact
Registry y unidad de arranque `ti-stack.service` habilitada. Su estado
inactive/dead observado en la auditoría requiere contraste con el ciclo de
backup; los13 contenedores funcionan. Cierre v2:174734 por motor; corte
16/11:176803. Objetivo USD5/día (estimado histórico4.08 con SKU oficiales,
no factura ni tope automático).
Acceso operativo por IAP SSH; Airflow UI solo por túnel (18081).
Codex App fue confirmado manualmente por el dueño. Una conexión ChatGPT
separada no se afirma. Alertas presupuestarias/facturación no verificadas
por IAM. Detalle histórico:
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
No usar `down -v` ni `--remove-orphans`. Límites: sin HA, sin transacción
distribuida ni garantías ante escritores externos concurrentes; cobertura
NVD parcial. HTTPS y sincronización NVD sí existen en cloud. La interfaz MCP
conserva defaults legacy y ofrece summary opt-in. Cambios productivos,
backfills y migraciones incompatibles requieren autorización explícita.
# Cassandra en Google Cloud: actualización del entorno

Véase [Cassandra distribuida en GCP](docs/architecture/cassandra-gcp-cluster.md)
para la topología, operación y evidencia posteriores al cierre académico de una VM.
El Compose de desarrollo local sigue usando una sola instancia por defecto.
