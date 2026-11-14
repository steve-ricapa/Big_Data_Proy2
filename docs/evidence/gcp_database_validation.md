# Validación de motores reales en GCP (VM ti-dev-data)

## Estado de cierre v2 — 11/11/2026

**174734 CVE únicos en cada motor**, cero IDs duplicados; huella común
`5d8d4de4bebf0d1cb4251cc7e7cc8c0e12fa255e13146ac5bd796e28581d02b1`.
Neo4j1488730 relaciones. Nueva corrida programada11/11 03:00 UTC:
2335 registros,127 nuevos/802 modificados/1406 unchanged por motor.
CRUD cloud12 PASS con limpieza; suite cloud55 PASS. Restauraciones aisladas
desde descarga GCS: tres motores PASS,174607 CVE y huella `1f3fe1f5...`,
correcta para el respaldo02:00 anterior al sync03:00.
Evidencia `acceptance_v2/final_state.json`, `crud.json`, `cloud_tests.xml`,
`restore_three.json`. El detalle siguiente es histórico del10/11, no el
estado posterior a la nueva sincronización.

## Histórico de carga y sincronizaciones del10/11
**Carga inicial: 171791 CVE por motor** con huella idéntica a la local
`1a60346f5dcdbe7ee928bc7a8cf22779abeeb2bdf23efa1f39f7c7c1c3c9fcd2`
(Mongo/Cassandra/Neo4j, etapa `verify`). La carga se reanudó desde
checkpoints tras un OOM de MongoDB (157200 registros, `mem_limit` 1g→2g en
`docker-compose.public.yml`), sin re-descargar feeds válidos; Neo4j terminó
171791/859 lotes en 335.8s con 0 modificados/huérfanos. Evidencia:
`gcp_initial_load_recovery.log` (línea `verify` final).

**Sincronización NVD real posterior (corrida programada 03:00 UTC en
catch-up)**: 5343 registros de la API 2.0, 0 inválidos, 0 duplicados, 2696
CVE nuevos → **174487 por motor** con paridad de huella
`b1e91d5db6d56ab776b1deaa60a6751afa2483657ab92be225165ac791c6a335` en los
tres. Replay full idempotente posterior: new=0 por motor, 2616 registros más
recientes protegidos como "stale" (sin regresión de contenido de la
sincronización), paridad mantenida.

**Estado tras sincronización manual del10/11 `sync34_20261110T215555`**:
ventana 19:11→21:51 UTC, 2207 registros en 2 páginas, 0 reintentos; 120 CVE
nuevos + 905 modificados + 1182 unchanged por solape idempotente →
**174607 CVE por motor** con paridad de huella
`1f3fe1f5ed51962dca77b6d039f3d7f77eedd6c0fc8736e5f71883e1ac33facf` en los
tres (etapa `verify`). Manifiestos por run: `data/staging/*/run.json` de la
VM; resumen en `gcp_airflow_execution.md`, journal completo en
`gcp_sync34_run.log`. pytest cloud: **53 passed** (`gcp_pytest.log`, CRUD
real por motor); 14 checks HTTP públicos PASS (`gcp_https_validation.json`).
pytest cloud: **53 passed** (`gcp_pytest.log`, CRUD real por motor); 14
checks HTTP públicos PASS (`gcp_https_validation.json`).

## Autenticación Cassandra
Usuarios de aplicación `ti_pipeline` (escritor) y `ti_reader` (lector) con
contraseñas en Secret Manager; login del superusuario por defecto
deshabilitado (`gcp_cassandra_users.log`). La aplicación nunca usa el
superusuario.

## Reglas de red verificadas
Solo 80/443 públicos hacia Caddy; 27017/9042/7687 sin publicación (red
Docker interna `data`, `internal: true`). Admin Keycloak/master 404 público
(`private_admin` PASS en `gcp_https_validation.json`). Acceso operativo: IAP
SSH OS Login.

## Contenedores
13 servicios running; nueve con healthcheck Docker healthy y cuatro con
sondas funcionales externas periódicas (`acceptance_v2/component_health.log`): mongodb 2g, cassandra,
neo4j, airflow3 postgres/api/scheduler/dag-processor, api, dashboard,
keycloak-db, keycloak, mcp-remote, caddy. Persistencia de arranque: unidad
systemd `ti-stack.service` habilitada (multi-user.target).

No se destruyó ninguna base ni volumen cloud para probar; las pruebas son de
lectura o CRUD académico controlado sobre el dataset real.
