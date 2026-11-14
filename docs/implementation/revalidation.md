# Revalidación autónoma — 10/11/2026, segunda revisión

Se encontró una implementación completa posterior a la estructura inicial;
se conserva, sin reescribir los adapters, ETL, dashboard o Terraform válidos.
Esta revisión distingue nuevas ejecuciones de las evidencias históricas.

## Resultados y diagnóstico

- Windows: 31 PASS, 6 SKIP por aislamiento de motores. XML:
  `docs/evidence/revalidation_unit_tests.xml`.
- Primer intento Docker: 31 PASS y 6 FAIL por DNS. Docker mostraba contenedores
  activos con EndpointID/IP vacíos y red sin miembros, no un fallo del parser.
- Recuperación: `docker compose up -d --force-recreate --wait mongodb cassandra
  neo4j postgres api dashboard --wait-timeout 360`. No se borraron volúmenes ni
  se tocaron contenedores de otros proyectos.
- Repetición Docker: **37 PASS, 0 FAIL, 0 SKIP**, XML
  `docs/evidence/revalidation_integration_tests.xml`.
- Verificación completa de los motores: 171791 CVE en cada uno y huella
  identidad/contenido igual a la evidencia anterior
  `1a60346f5dcdbe7ee928bc7a8cf22779abeeb2bdf23efa1f39f7c7c1c3c9fcd2`.
- HTTP: primer intento dio 503 por timeout del conteo Mongo durante verificación
  concurrente en caché fría. Repetición secuencial: 12 comprobaciones correctas.
  Se revisará el conteo sin filtros para evitar escanear documentos completos.
- Terraform CLI temporal existente encontrado; `validate` PASS. Proyecto gcloud
  activo correcto. No se solicitaron credenciales ni se imprimieron tokens.

## Trabajo activo

Evaluar migración Airflow en imagen/metadata separadas para preservar el
historial 2.11. No declarar cerrada la seguridad por cambiar un tag.

## Cierre de esta revisión

Ensayo adicional **full Airflow SUCCESS**, run `full34_20261110T170841`,171791
válidos,0 inválidos/duplicados,siete SUCCESS yNeo4j intento2. Todos unchanged,
0escrituras en cada motor y paridad final id/hash: replay completo real sobre
almacenes previamente cargados. Manifiesto/exportación/captura `airflow34_full_*`.
Índices publicación/año redujeron consultas medidas ~5.5s a0.36/0.08s en esta
máquina; no es benchmark universal. `filter_validation.json`:cuatro filtros PASS.

- Airflow3.4 slim/lock con hashes: construido, pip check PASS, auditoría final
  145 paquetes y0 hallazgos Python conocidos. Metadata2.11 intacta/detenida.
- Scheduler real dos runs10000 con siete SUCCESS y Neo4j retry2; última
  `migration34_20261110T165908`, con Mongo writer readWrite en lugar de admin.
- Test suite final42PASS/0FAIL/0SKIP Docker; Windows35PASS/7SKIP.
  Tests adicionales: fechas reales/rango,conteo indexado,MCP y read-only Mongo.
- Cinco regresiones incrementales reales PASS con writer; nueve checks KPI
  independientes PASS tras el DAG;14HTTP PASS y MCP protocolo real PASS.
- Reader Mongo rechaza escritura con Unauthorized; API sigue consultando datos.
- Overlay Compose, scripts Bash y sintaxis PowerShell PASS; ruff PASS.
- Terraform fmt/init/validate/plan repetidos,37altas/0cambios/0bajas,sin apply.
- Capturas nuevas reales: `revalidation_dashboard_cassandra.png`,
  `airflow34_dag.png`, `airflow34_success.png`.
- Full: `airflow34_full_success.png` ymanifiesto validan replay171791; los tres
  originales nuevamente verificados al finalizar en `final_raw_integrity.json`.
- Estado generado desde artefactos reales: `revalidation_state.json`.

Incidencias corregidas: asyncpg requerido por API Airflow3; archivo de SimpleAuth
no puede ser secret readonly y se materializa privado sin mostrarlo; rutas
MSYS requieren no conversión; SDK MCP Windows necesita entorno normal Docker
para descubrir Compose. No se modificaron ADC ni recursos GCP.
