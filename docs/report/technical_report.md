# Threat Intelligence Platform — Informe técnico

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

**Big Data II · entrega objetivo 16/11/2026 · revisión de cierre 11/11/2026**

Estado de aceptación: `final_acceptance_v2.md`. Los cortes históricos se
identifican expresamente; no son conteos actuales ni pruebas repetidas.

## 1. Introducción
NIST NVD publica documentos CVE enriquecidos con métricas CVSS, debilidades CWE y configuraciones CPE. El proyecto integra esa información en modelos documental, orientado a consultas y de grafo. Se distingue vulnerabilidad declarada de ataque confirmado.

## 2. Planteamiento del problema
Un JSON de gran tamaño no ofrece por sí solo navegación, actualizaciones controladas, análisis por producto ni exploración de relaciones. Consultas repetidas directamente sobre 1.12GB elevan latencia y dificultan reproducibilidad. Se requiere trazabilidad de fuentes, calidad, persistencia idempotente e indicadores interpretables.

## 3. Objetivos
Procesar más de 50000 registros semiestructurados; almacenar en MongoDB, Cassandra y Neo4j reales; coordinar siete etapas con Airflow; demostrar CRUD e incrementalidad; ofrecer cinco o más KPI y dashboard; operar el despliegue GCP autorizado con evidencia y dentro del objetivo presupuestario estimado.

## 4. Justificación de Big Data
Volumen original: 171791 entradas/1117082537 bytes; variedad: campos anidados, métricas y versiones distintas, arrays CWE/CPE/referencias; variabilidad y veracidad: faltantes, versiones modificadas y dependencias de configuración. No se presenta 1.12GB como escala industrial masiva. La carga inicial usa streaming de archivos; la actualización cloud descarga páginas NVD API 2.0 diariamente a las 03:00 UTC, con watermark solo tras paridad. No es streaming de eventos en tiempo real.

## 5. Caracterización del dataset
Tres feeds locales NVD 2.0 de 2024/2025/2026: 39369, 45482 y 86940 entradas respectivamente. Inventario real, SHA256 y metadatos en `docs/evidence/inventory.json`. El año del feed/ID no define necesariamente la fecha publicada. Solo el resultado final de validación demuestra cantidad única válida; inventario no equivale a calidad semántica. No se redescargaron fuentes completas.

## 6. Arquitectura de solución
Consultar `docs/architecture/system.md` y `data_flow.md` para diagramas. Airflow/CLI comparte paquete Python. NDJSON canónico conecta etapas sin XCom grande. PostgreSQL almacena metadatos Airflow; SQLite es auxiliar de dedup/checkpoint, nunca sustituto de las bases exigidas. API FastAPI separa consultas del dashboard Streamlit.

GCP desplegado: una VM e2-standard-4 en us-central1-a, discos 30+100 GiB,
2 buckets privados, 1 repositorio Artifact Registry, 10 secretos administrados
y 5 políticas Monitoring (inventario API `acceptance/gcp_inventory.json`).
Son 13 servicios: 9 con healthcheck Docker y 4 con sondas funcionales externas
activas por `ti-component-health.timer`. Sus healthchecks nativos están también
declarados en Compose, pero no se fuerza recreación para activarlos.

## 7. Modelo MongoDB
`cves` conserva `raw_cve` y campos canónicos, ID único e índices secundarios. Validador básico y normalizador validan contrato. Upsert por identidad. KPI y ejecuciones verificadas en colecciones separadas. CRUD real con ID sintético aislado; documentación `docs/data_models/mongodb.md`.

## 8. Modelo Cassandra
Tablas por ID, severidad/mes, producto/mes, CWE/mes, snapshot KPI. Clustering por publicación descendente e ID, sin joins ni ALLOW FILTERING. Particiones mensuales limitan crecimiento, pero la medición completa de tamaños/compaction sigue siendo trabajo de escalado. RF=1 académico, sin tolerancia a pérdida. Reintento idempotente y eliminación de claves obsoletas usando proyecciones previas. Ver `docs/data_models/cassandra.md`.

## 9. Modelo Neo4j
Nodos CVE/CWE/Product/Vendor/CPE/Reference con constraints únicos; relaciones extraídas de configuraciones vulnerables y referencias. CPE conserva versiones y producto deduplica `[part,vendor,product]`. MERGE y reconstrucción de relaciones salientes en transacción. Nodos compartidos/huérfanos no se eliminan. No se infiere explotación ni fabricante verificado fuera de NVD. Ver `docs/data_models/neo4j.md`.

## 10. Pipeline Airflow
DAG `nvd_threat_intelligence`: extract → validate → load_mongodb → load_cassandra → load_neo4j → calculate_kpis → verify. Schedule diario 03:00 UTC, 2 reintentos exponenciales, máximo una tarea/run activo. XCom solo paths. `airflow dags test` ejecutó siete tareas con 1000 entradas: evidencia `airflow_dag_test.log`. Esa ejecución no demuestra por sí sola disparo por cron; scheduler/UI se verifican separadamente. No hay backfill de snapshots históricos ausentes.

Runtime recomendado migrado a **Airflow3.4.0** con metadata separada, proveedor
standard y lock de hashes. Dos ejecuciones scheduler reales con10000 entradas
terminaron siete tareas SUCCESS; Neo4j falló una vez deliberadamente y pasó en
intento2. Última `migration34_20261110T165908` usa identidad Mongo writer.
Evidencias `airflow34_scheduler_retry.json`, `airflow34_success.png`.

## 11. Procesamiento incremental
Hash SHA256 de contenido, lastModified normalizado UTC, estado independiente por motor. Nuevo, modificado, sin cambios, obsoleto. Commit después de escritura correcta; fallo parcial se repite. Checkpoints en volumen Docker compartido por runner/Airflow. La dedup SQLite inicial sobre bind Windows resultó lenta: trabajo temporal se trasladó al disco del contenedor, conservando artefactos y fuentes. No ejecutar dos pipelines concurrentes; no hay locking distribuido para escritores externos.

## 12. KPI
Catálogo con fórmulas/reglas/fuentes en `docs/kpis/catalog.md`: total único, severidad, meses, CWE, producto/fabricante, medias CVSS por versión, cambios 30 días, grafo y productos únicos. Preferencia 4.0 >3.1 >3.0 >2.0, sin promedio global mezclado. UNKNOWN no se convierte a cero. Población incluye Rejected, identificado separadamente. Rankings no equivalen a exposición real de una organización.

## 13. Dashboard
Cinco vistas: Overview, Vulnerability Explorer, Threat Analytics, Graph Intelligence,
Data Pipeline. API paginada, caché 30s e invalidación manual. Fecha de snapshot
explícita; no cifras inventadas si API falla. Subgrafo limitado a 250 relaciones.
Threat Analytics consulta un snapshot directamente en Cassandra y compara su
fecha con Mongo; el resto consulta Mongo y Neo4j mediante API. No se afirma
que cada gráfico consulte los tres motores simultáneamente. Fechas API son
calendáricas y el conteo sin filtros usa índice. Mongo usa identidad read-only.

## 14. CRUD
Doce operaciones reales en motores GCP, cuatro por motor, verificadas con lectura tras escritura/actualización y ausencia tras borrado. Cierre v2: `acceptance_v2/crud.log`, ID temporal aleatorio `CVE-2099-187069189812724775`, cleanup_verified=true. No se modifican CVE reales ni se inicializan esquemas en este probe. Limpieza en finally y propiedad de la identidad antes de borrar; Cassandra añade IF NOT EXISTS y TTL. `crud.json` original queda como evidencia histórica local.

## 15. Pruebas
**Cierre v2 nuevo: 55 PASS/0 FAIL/0 SKIP en cloud**, con integración real de
tres motores y pruebas de permisos; **47 PASS/8 SKIP en Windows** (requieren
integración Docker). Logs `acceptance_v2/cloud_tests.log` y
`acceptance_v2/local_tests.log`; no sumar ambas ejecuciones.
El test cloud monta código y tests actuales en una imagen de pruebas, sin
reemplazar contenedores productivos. Las operaciones CRUD usan solo IDs temporales.
Adicionales nuevos de auditoría: HTTPS autenticado, cinco vistas Chrome,
MCP/OAuth y seis herramientas, y seis KPI contrastados con agregaciones Mongo.
Evidencia `acceptance/http.json`, `browser.json`, `mcp.json`, `quality.json`.
Conteos/huella id/hash no prueban cada arista/proyección secundaria. Prueba real
demuestra que usuario Mongo de API lee y no puede escribir (Unauthorized13).

**Histórico anterior, 10/11/2026**: pytest en contenedor cloud **53 PASS**; checks
HTTPS públicos PASS (401 sin auth, admin Keycloak/master 404, TLS 1.3);
protocolo MCP/OAuth completo PASS (PKCE S256 con consentimiento, código
replay rechazado, seis herramientas, id inválido rechazado); 12 pruebas
locales de sync/MCP remoto PASS y ruff PASS. `gcp_pytest.log`,
`gcp_https_validation.json`, `gcp_mcp_protocol_validation.json`.

## 16. Resultados
**Corte cloud de cierre v2, 11/11/2026**: 174734 CVE únicos por motor,
0 IDs duplicados, huella común `5d8d4de4bebf0d1cb4251cc7e7cc8c0e12fa255e13146ac5bd796e28581d02b1`.
Neo4j: 1488730 relaciones; 23082 productos únicos. Seis comprobaciones KPI
independientes coincidieron (`acceptance_v2/final_state.json`, `quality.json`).
La corrida automática del11/11, 03:00:46–03:02:32 UTC (105.84s, 7 SUCCESS),
procesó2335 registros:127 nuevos/802 modificados/1406 unchanged por motor.
La sincronización diaria puede
cambiar el siguiente corte; usar el resultado final v2, no un total fijo, en demo.

Respaldo diario11/11 02:00: restauraciones nuevas de MongoDB, Cassandra y
Neo4j desde objetos descargados de GCS privado, red none y volúmenes scratch:
**3 PASS**,174607 CVE por motor y huella anterior al sync03:00. No se
sobrescribieron bases productivas (`acceptance_v2/restore_three.json`).
Cuatro imágenes app/test/MCP/Airflow se reconstruyeron con etiquetas de
verificación; contenedores productivos sin reemplazo. Se validaron Compose,
scripts Bash/PowerShell, uv.lock y Terraform. No se recreó la VM ni se probó
un host vacío o igualdad byte a byte de las imágenes; bases fijadas por tag,
no digest. Docker Desktop local estaba detenido: el build se ejecutó en la VM.

### Histórico de cargas y ensayos previos (no estado cloud actual)

**Carga inicial completa:171791 CVE únicos en cada motor**,0 inválidos/duplicados y misma huella de todos los pares id/hash. Mongo159.686s,Neo4j304.868s son etapas concretas,no duración total. Cassandra confirmó escrituras y falló en COUNT(*);recuperación con paginación1000 tomó100.27s y detectó171791 sin cambios,0 reescrituras. Evidencias:full_optimized.log/full_recovery.log/delivery_state.json.

KPI completos:17707 críticos,21784 productos únicos,56119 modificados30d,4004 Rejected;CVSS3.1 promedio6.9126(n119816),4.0 promedio6.2391(n42945),3.0 promedio7.3211(n1392). Grafo617044 nodos/1467881 relaciones. Nueve comprobaciones independientes de KPI PASS;37 pytest Docker PASS/0FAIL/0SKIP,incluye6 integración;12 HTTP PASS y cinco vistas capturadas.

Esas cifras son del primer corte histórico. La revalidación posterior conserva
171791 y paridad completa; los KPI se recalcularon tras Airflow3 y nueve checks
independientes pasaron. Suite posterior42PASS yHTTP14PASS sustituyen los
conteos de pruebas anteriores. `revalidation_state.json` reúne ese corte histórico.
Auditoría Python del runtime3.4:145 paquetes/0avisos conocidos; aplicación con
MCP63 paquetes/0avisos conocidos. No auditoría completa OS/JVM/seguridad externa.

Airflow ejecutó1000 por dags test y10000 por scheduler,run `resilience_20261110T085141`,7 SUCCESS. Conexión Neo4j deliberadamente rechazada en intento1 produjo UP_FOR_RETRY;intento2 tuvo éxito. DAG pausado al terminar. La carga171791 fue por CLI compartida,no un full Airflow. No usar run_duration de dags test como benchmark:parte de fecha lógica. No extrapolar capturas sample1000 a resultados finales.

**Cierre posterior full Airflow3**: `full34_20261110T170841` ejecutó los tres
feeds completos,171791 únicos válidos,0 inválidos/duplicados y siete tareas
SUCCESS. Replay detectó171791 unchanged/0escrituras en cada motor, con paridad
final de todos los ID/hash. Neo4j superó fallo deliberado en intento2. Esta
ejecución sí acredita replay completo Airflow; la carga inicial vacía fue CLI.
Evidencias `airflow34_full.json`,manifiesto exportado yPNG full real.

**Despliegue GCP verificado**: la misma plataforma corrió en una VM
e2-standard-4 con 13 contenedores, HTTPS TLS 1.3 y OIDC real. La corrida
programada 03:00 UTC ejecutó sincronización NVD API 2.0 real (5343 registros,
+2696 CVE) y la manual etiquetada `sync34_20261110T215555` añadió +120 CVE
más con solape idempotente (1182 unchanged): **174607 CVE por motor** con
paridad de huella y watermark avanzado solo tras verify. Dos replays full
cloud entre ambas sincronizaciones confirmaron new=0 y protección "stale" de contenido más
reciente. Evidencia: `gcp_airflow_execution.md`, `gcp_database_validation.md`.

## 17. Costos
Terraform aplicado en GCP tras gate de costo previo (USD 4.08/día, 4.90 con 20% contingencia, SKU oficiales us-central1, no factura): una VM std4 con discos 30+100 GiB, IP reservada, buckets privados, Secret Manager, Artifact Registry y observabilidad. Sin CloudRun/NAT/GKE/GPU/balanceadores. Plan final sin deriva. Alertas presupuestarias bloqueadas por IAM de facturación y documentadas para el administrador. Fuentes: `gcp_preapply_cost_gate.json`, `gcp_actual_costs.md`, `gcp_cost_estimate.md` (escenarios). Conservar 30% del crédito como margen. Apagar VM no elimina cobros de almacenamiento.

## 18. Limitaciones
Entorno académico, un nodo por motor en una sola VM, sin HA. Cloud despliega TLS 1.3 real (Caddy, hostname sslip.io con IP reservada estable) y Cassandra con auth de app, pero Neo4j Community y Cassandra requieren más controles antes de producción. La sincronización NVD automática diaria está implementada y verificada con CVE reales; el descargador descarta ventanas incompletas y cuarentena registros inválidos. MCP remoto con OIDC/PKCE verificado por HTTPS; la conexión de la cuenta ChatGPT exige login manual del dueño (documentado, no simulado). No auditoría exhaustiva de semántica CVE fuera del contrato. Backfill relee archivos disponibles. CPE AND/OR se conserva en original; aristas simplifican aplicabilidad. No confundir un grafo de asociaciones con incidentes observados.

## 19. Conclusiones
La solución demuestra persistencia poliglota, ETL compartida y consultas analíticas sobre documentos NVD sin cargarlos íntegros en RAM. Idempotencia y checkpoints por motor permiten recuperación de fallos parciales. El despliegue GCP verificado extiende el mismo diseño a operación real: HTTPS público con autenticación, sincronización NVD diaria con watermark tras paridad, respaldo frío coordinado y restauración aislada verificada, dentro del objetivo de USD 5/día estimado. La defensa debe citar resultados ejecutados, población, fecha y cobertura; la conexión de la cuenta ChatGPT del dueño queda como paso manual verificado en su mecanismo, no como afirmación.

## 20. Referencias
- NIST NVD Data Feeds: https://nvd.nist.gov/vuln/data-feeds
- NVD CVE API/documentación: https://nvd.nist.gov/developers/vulnerabilities
- FIRST CVSS: https://www.first.org/cvss/
- Apache Airflow 2.11: https://airflow.apache.org/docs/apache-airflow/2.11.0/
- Apache Airflow 3.4 (runtime recomendado): https://airflow.apache.org/docs/apache-airflow/3.4.0/
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MongoDB: https://www.mongodb.com/docs/manual/
- Cassandra data modeling: https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/
- Neo4j Cypher MERGE: https://neo4j.com/docs/cypher-manual/current/clauses/merge/
- Streamlit: https://docs.streamlit.io/
- Terraform Google provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Google Cloud precios: https://cloud.google.com/products/compute/pricing/general-purpose

Referencias son documentación técnica oficial, no artículos científicos inventados.
Resultados vigentes y límites de reconstrucción/restauración: `final_acceptance_v2.md`.
No se afirma conexión desde ChatGPT ni reproducción byte a byte de imágenes.
