# Resultados de pruebas — ejecución local

**Resultado vigente:42PASS/0FAIL/0SKIP Docker**,35PASS/7SKIP Windows.
Airflow3 full171791: siete SUCCESS,Neo4j intento2,0duplicados/0escrituras,
paridad final entre motores;`airflow34_full.json` ymanifiesto exportado.
Detalles y cobertura en la actualización al final de este documento y
`revalidation_state.json`. Los apartados37/31 siguientes son históricos.

**Primer cierre histórico10/11/2026:37 PASS,0 FAIL,0 SKIP en Docker**,incluye6 integración real. Windows31PASS/6SKIP. No sumar suites que repiten unitarias. Fuentes históricas:integration_tests.xml/log,delivery_state.json. Nueve checks KPI independientes PASS;12 HTTP reales PASS;cinco vistas/PNG verificadas. Carga171791 por motor con paridad de todos los IDs/hashes. Scheduler10000 con7 SUCCESS y Neo4j2 intentos,logs UP_FOR_RETRY y éxito.

## Historial anterior al cierre
La tabla siguiente registra verificaciones parciales anteriores;los pendientes que aparecen en ella quedaron cerrados por las evidencias finales anteriores y progress.md.

| Verificación | Resultado confirmado | Evidencia |
|---|---|---|
| Pytest local |30 PASS,0 FAIL,6 SKIP de integración opt-in|unit_tests.xml|
| Inventario |171791 entradas/3 feeds/hashes coinciden|inventory.json|
| Motores reales |Mongo8.0.12,Cassandra4.1.9,Neo4j5.26.12 saludables|smoke100.log,sample1000.log|
| CRUD |12 operaciones PASS|crud.json/crud.log|
| Incremental |5 escenarios agregados PASS|incremental.json/incremental.log|
| DAG1000 |7 tareas SUCCESS, DagRun success, `dags test`|airflow_dag_test.log|
| API/dashboard HTTP |12 comprobaciones reales PASS|http_validation.json|
| Dependencias app |pip-audit sin vulnerabilidades conocidas reportadas|dependency_audit.json/log|
| Terraform |init/validate/plan correctos;37 altas NO aplicadas|terraform_init.log,terraform_validate.txt,terraform_plan.txt|
| Carga completa optimizada |En ejecución, no declarada exitosa aún|full_optimized.log y manifiesto final|
| Scheduler retry real |Preparado, pendiente ejecución aislada|fail_neo4j_once=false por defecto|

Pytest incluye conexión fallida simulada,checkpoint tras fallo parcial/recuperación,normalización/streaming/dedup/CPE/CVSS/KPI/routing,empate de hash independiente del orden y fabricantes únicos por CVE. No usa bases reales para esas30 pruebas. Integración opt-in: `docker compose build tester` y `docker compose run --rm tester -q --junitxml=docs/evidence/integration_tests.xml`; no contar antes de ejecutarse.

Advertencia Starlette/TestClient/httpx de compatibilidad futura no impidió tests. Auditoría cubre lock app, no certifica imágenes/JVM/Airflow ni ausencia total de vulnerabilidades. CI preparado pero no ejecutado remotamente: carpeta sin Git, sin commits/pushes.

Incidencias corregidas: paréntesis DAG detectado por compileall; lint; puertos web no publicados en red interna, separada edge; I/O SQLite Windows lento, trasladado a disco/volumen Docker. Intento `full_load.log` detenido deliberadamente para optimizar (exit137 por parada, no evidencia de OOM); no se presenta como carga completa exitosa.
# Actualización vigente — segunda revisión 10/11/2026

**42 PASS,0 FAIL,0 SKIP en Docker** (`revalidation_integration_tests.xml/.log`),
35PASS/7SKIP Windows (`revalidation_unit_tests.xml`); no sumar suites repetidas.
Siete integración incluyen CRUD/salud tres motores y rechazo escritura Mongo
reader. Cinco regresiones incrementales PASS; nueve checks KPI PASS;14HTTP PASS.
MCP SDK real: initialize,listado6,consultas6,rechazo identificador PASS.
Airflow3.4 scheduler10000: siete SUCCESS,Neo4j intento2; `airflow34_scheduler_retry.json`.
Ruff,Bash,parser PowerShell,Compose raíz/overlay,Terraform fmt/init/validate/plan PASS.
Sin full Airflow ni recursos cloud. Estado completo en `revalidation_state.json`.

## Histórico de pruebas previas
