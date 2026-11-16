# 08 — Inventario técnico de archivos

Todas las rutas son relativas al repositorio y fueron verificadas el
16/11/2026 (commit `6d947ce`). Relevancia: ★★★ núcleo académico · ★★ soporte · ★ anexo.

## Pipeline / ETL

| Componente | Ruta | Función | Relevancia |
|---|---|---|---|
| DAG | `airflow/dags/nvd_pipeline.py` | DAG 7 tareas, schedule, retries, params | ★★★ |
| Pipeline | `src/threat_intelligence/pipeline.py` | prepare/validate/load×3/kpis/verify + huella | ★★★ |
| Normalización | `src/threat_intelligence/transformations/normalize.py` | CVE→canónico, CVSS, CPE, hash | ★★★ |
| Sync NVD | `src/threat_intelligence/ingestion/sync.py` | descarga incremental, watermark | ★★★ |
| Lectura feeds | `src/threat_intelligence/ingestion/nvd.py` | streaming ijson + inventario hashes | ★★ |
| Checkpoints | `src/threat_intelligence/incremental/state.py` | dirty-check por motor | ★★★ |
| KPIs | `src/threat_intelligence/analytics/kpis.py` | cálculo de todos los indicadores | ★★★ |
| Auditoría KPI | `src/threat_intelligence/analytics/audit.py` | recalcula independientemente | ★★★ |
| CLI | `src/threat_intelligence/cli.py` | run/sync/crud/verify/audit-kpis | ★★ |
| CRUD | `src/threat_intelligence/crud.py` | CRUD seguro 3 motores con cleanup | ★★★ |
| Config | `src/threat_intelligence/common/config.py` | settings + secrets por archivo | ★★ |
| Selftest | `src/threat_intelligence/selftest.py` | regresión incremental | ★ |

## Bases de datos (adapters = esquema ejecutable)

| Componente | Ruta | Función | Relevancia |
|---|---|---|---|
| MongoDB | `src/threat_intelligence/databases/mongodb/__init__.py` | validator, índices, upserts | ★★★ |
| Cassandra | `src/threat_intelligence/databases/cassandra/__init__.py` | tablas CQL, deletes de claves viejas | ★★★ |
| Neo4j | `src/threat_intelligence/databases/neo4j/__init__.py` | constraints, MERGE, reconstrucción aristas | ★★★ |
| Doc modelos Mongo | `docs/data_models/mongodb.md` | modelo + decisiones índices | ★★★ |
| Doc modelos Cassandra | `docs/data_models/cassandra.md` | partition keys + ejemplos CQL | ★★★ |
| Doc modelos Neo4j | `docs/data_models/neo4j.md` | grafo + ejemplos Cypher | ★★★ |
| Doc BD nativas | `database/README.md` | dónde vive el esquema ejecutable | ★★ |

## API / Dashboard / MCP

| Componente | Ruta | Función | Relevancia |
|---|---|---|---|
| API | `services/api/app.py` | endpoints lectura, validación estricta | ★★★ |
| Vistas/API | `services/api/views.py` | applicability CPE, metadata, catálogo | ★★★ |
| Dashboard | `services/dashboard/app.py` | 5 vistas Streamlit | ★★★ |
| MCP stdio | `services/mcp_server/server.py` | 6 herramientas | ★★ (adicional) |
| MCP remoto | `services/mcp_server/remote.py` | OAuth OIDC + transport security | ★★ |
| Contratos MCP | `services/mcp_server/contracts.py` | esquemas cerrados, redacción | ★ |
| README MCP | `services/mcp_server/README.md` | config agentes | ★ |
| Verificador dashboard | `scripts/verify_dashboard_readonly.py` | suite AppTest 15 checks | ★★★ |
| Verificador MCP | `scripts/verify_mcp_comprehensive.py` | suite semántica SDK→HTTP | ★★ |
| Verificador MCP nativo | `scripts/verify_mcp_comprehensive_native.py` | vía runtime Codex | ★ |
| Verificador HTTP | `scripts/verify_http.py` / `verify_filters.py` | API y rendimiento filtros | ★★ |

## Infraestructura

| Componente | Ruta | Función | Relevancia |
|---|---|---|---|
| Compose base | `docker-compose.yml` | motores + runner + api + dashboard | ★★★ |
| Overlay Airflow3 | `docker-compose.airflow3.yml` | Airflow 3.4 con metadata propia | ★★★ |
| Overlay seguridad | `docker-compose.secure.yml` | roles Cassandra, secrets | ★★★ |
| Overlay público | `docker-compose.public.yml` | Keycloak, Caddy, MCP, puertos | ★★★ |
| Dockerfile app/test/mcp | `infrastructure/docker/python.Dockerfile` | imágenes con locks por hash | ★★ |
| Dockerfile Airflow | `infrastructure/docker/airflow3.Dockerfile` | imagen Airflow 3.4 | ★★ |
| Dockerfile dashboard | `infrastructure/docker/dashboard.Dockerfile` | imagen separada dashboard | ★★ |
| Caddyfile | `infrastructure/docker/Caddyfile` | TLS + rutas + bloqueos admin | ★★ |
| Terraform dev | `infrastructure/terraform/environments/dev/*.tf` | ensamblaje del entorno | ★★★ |
| Módulo secrets | `infrastructure/terraform/modules/secrets/main.tf` | contenedores Secret Manager (código) | ★★ |
| Resto módulos TF | `infrastructure/terraform/modules/{networking,compute,iam,storage,registry,observability,cloud_run}/main.tf` | infra por dominio | ★★★ |
| Bootstrap VM | `infrastructure/scripts/vm-bootstrap.sh` | docker + montaje disco (no formatea) | ★★ |
| systemd unidades | `infrastructure/scripts/ti-{stack,backup.*,health.*,component-health.*}` | arranque/backup/sondas | ★★ |
| Instalación cloud | `scripts/cloud_install.py` | bootstrap VM existente (sensible) | ★ |
| Backup | `scripts/cloud_backup.py` + `scripts/backup_local.py` | backup frío + GCS privado | ★★★ |
| Restore | `scripts/cloud_restore_three.py` | restauración aislada 3 motores | ★★★ |
| Remoto GCP | `scripts/gcp_remote.py` | IAP SSH/SCP wrapper | ★★ |
| Credenciales test | `scripts/cloud_test_credentials.py` | transferencia privada por IAP | ★ |
| Preparación local | `scripts/prepare_{local,security,airflow3}.py` · `scripts/start-local.ps1` | setup local sin exponer secretos | ★★ |

## Pruebas

| Componente | Ruta | Función | Relevancia |
|---|---|---|---|
| Suite completa | `tests/` (conftest.py fixture CVE) | 94 PASS actuales | ★★★ |
| API | `tests/test_api.py` | contratos HTTP | ★★ |
| MCP | `tests/test_mcp.py`, `test_remote_mcp.py`, `test_mcp_comprehensive.py` | contratos herramientas | ★★ |
| Dashboard | `tests/test_dashboard.py` | UI con fixture HTTP local | ★★★ |
| Inputs entrega | `tests/test_delivery_inputs.py` | módulos TF + política Git | ★★ |
| Integración (opt-in) | `tests/test_integration.py` | CRUD/permisos REALES | ★★★ |
| Núcleo/pipeline/sync | `tests/test_core.py`, `test_pipeline.py`, `test_sync.py` | normalización/idempotencia | ★★★ |
| Estructura DAG | `airflow/tests/test_dag_structure.py` | DAG parsea, 7 tareas | ★★ |

## Documentación y evidencias clave

| Componente | Ruta | Función | Relevancia |
|---|---|---|---|
| README | `README.md` | guía instal/uso actual (post-cierre) | ★★★ |
| Auditoría final | `docs/audits/technical_deliverables_audit.md` | 7/3→10/10 con evidencia | ★★★ |
| Cierre técnico (evidencias) | `docs/evidence/technical_closure/` (README guía) | paridad, dashboard, TF, MCP manual | ★★★ |
| Capturas dashboard 16/11 | `docs/evidence/technical_closure/screenshots/*.png` | 5 vistas reales | ★★★ |
| Arquitectura | `docs/architecture/system.md`, `data_flow.md` | diagramas y responsabilidades | ★★★ |
| GCP desplegado | `docs/architecture/gcp_deployed_architecture.md`, `gcp-operations.md` | operación/TLS | ★★ |
| Costos | `docs/architecture/gcp_cost_estimate.md`, `gcp_actual_costs.md` | estimaciones con supuestos | ★★ |
| KPIs | `docs/kpis/catalog.md` | fórmulas y limitaciones | ★★★ |
| Decisiones | `docs/implementation/decisions.md` (32 decisiones) | por qué de cada elección | ★★★ |
| Requisitos | `docs/implementation/requirements.md` | matriz 17 criterios (del equipo) | ★★ |
| Remediación MCP | `docs/integrations/mcp_comprehensive_remediation.md` | X01–X04 + evidencias | ★ |
| CRUD evidencia | `docs/evidence/acceptance_v2/crud.json` | 12 PASS histórico | ★★★ |
| Restore evidencia | `docs/evidence/acceptance_v2/restore_three.json` | 3 PASS histórico | ★★★ |
| Idempotencia | `docs/evidence/airflow34_full_manifest.json` | replay unchanged | ★★★ |
| CI | `.github/workflows/quality.yml` | pytest+ruff+compile on push | ★★ |
| Locks | `requirements.lock`, `requirements-mcp.lock`, `uv.lock`, `airflow/requirements.lock` | reproducibilidad con hashes | ★★ |
| Ejemplo respuestas | `.env.example`, `infrastructure/terraform/environments/dev/terraform.tfvars.example` | plantillas sin secretos | ★ |
