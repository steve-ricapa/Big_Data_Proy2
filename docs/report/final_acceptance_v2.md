# Aceptación final v2 — Big Data II / GCP

**11/11/2026.** Sustituye el cierre operativo anterior, no sus evidencias históricas.
Resultados nuevos en `docs/evidence/acceptance_v2/` (rutas abreviadas abajo).
No se ejecutó Terraform apply/destroy, no se recreó la VM ni se reemplazaron
imágenes productivas. OAuth/MCP y los CVE reales no fueron modificados por las pruebas.

| Requisito / componente | Estado | Evidencia ejecutada | Pendiente / límite |
|---|---|---|---|
| 1. GCP, Terraform y reconstrucción controlada | PASS | `terraform_fmt.log`, `terraform_validate.log`, `terraform_plan.log`: válidos y sin deriva. Cuatro builds app/test/MCP/Airflow con etiquetas `ti-v2-*:verification`, sin reemplazo de contenedores (`rebuild.json`). Bash/PowerShell/Compose/uv.lock validados (`input_validation.json`); bundle con `.dockerignore` y exclusiones comprobadas. | No se reconstruyó VM/host vacío, no se probó apply ni igualdad byte a byte; bases por tag, no digest. |
| 2. Docker y healthchecks sin interrupción | PARTIAL | 13 servicios operativos: **9 checks Docker healthy + 4 sondas funcionales PASS** para Caddy, Keycloak, MCP y DAG Processor (`final_state.json`, `component_health.json`). Timer externo activo; resultados integrados a `unhealthy_containers`, Monitoring/Logging PASS, cero no saludables (`monitoring_live.log`). | Los cuatro checks nativos están en Compose; activarlos en contenedores existentes requiere recreación. No se forzó interrupción. |
| 3. MongoDB | PASS | **174734 CVE únicos**,0 duplicados, índice único y huella completa (`final_state.json`). | Corte posterior a sync03:00. |
| 4. Cassandra | PASS | **174734 únicos**,0 duplicados, SELECT paginado y huella igual a MongoDB. | — |
| 5. Neo4j | PASS | **174734 CVE únicos**,0 duplicados, **1488730 relaciones** y huella igual entre los tres motores. | — |
| 6. Airflow3.4.0 | PASS | DAG finalmente **ACTIVO**, sin runs activos. Última programada11/11: **03:00:46–03:02:32 UTC,105.84s,7 tareas SUCCESS**, intento1 (`final_state.json`). Pausa temporal durante restore y reactivación verificadas. | No se confunde actividad del DAG con éxito del run. |
| 7. Incrementalidad y CRUD cloud seguro | PASS | Última sync:2335 procesados,**127 nuevos/802 modificados/1406 unchanged por motor**. **12 operaciones CRUD PASS**, ID temporal y cleanup_verified=true (`crud.json`). Regresión repite CRUD; escaneo final sin duplicados/temporales. | No se escribieron CVE reales; no se inicializaron esquemas en el probe CRUD. |
| 8. Dashboard | PASS | Cinco vistas Chrome con datos y **SVG Neo4j renderizado** (`browser.json`, `screenshots/`). | Capturas fechadas; cifras avanzan con el schedule. |
| 9. API HTTPS | PASS | Health/ready, búsqueda/detalle, rankings, snapshot Cassandra y relaciones responden200; total174734 (`http.json`). | Acceso autenticado. |
| 10. MCP remoto | PASS | OAuth/PKCE, initialize/list_tools, **6/6 herramientas**, rechazo de código reutilizado e identificador inválido (`mcp.json`). | Cuenta ChatGPT del dueño: conexión efectiva no verificada. |
| 11. Respaldo y restauración de tres motores desde GCS | PASS | Respaldo diario `20261111T020125`: descarga nueva de **3 archivos GCS privados**, tamaños/SHA256 válidos; restore MongoDB/Cassandra/Neo4j en red none y volúmenes scratch, **174607 únicos/huella correcta por motor**, Neo4j1488142 relaciones (`restore_three.json`). | Es el corte02:00, anterior a producción03:00. Scratch detenidos, conservados para inspección; no se restauró Keycloak/Airflow. |
| 12. Seguridad | PASS | TLS1.3,401 sin autenticación, admin404; BD privadas. Secretos excluidos del bundle/build; inventario10 recursos Secret Manager y5 políticas Monitoring (`gcp_inventory.json`, `summary.json`). | Alcance académico, no pentest/HA/certificación. |
| 13. Regresión completa | PASS | **Cloud55 PASS/0 FAIL/0 SKIP** usando imagen de prueba reconstruida y código actual (`cloud_tests.xml`, `verification-image.json`); **Windows47 PASS/8 SKIP** por integración Docker (`local_tests.log`). Ruff PASS. Seis KPI reconciliados independientemente (`quality.json`). | No sumar ambas suites. Docker Desktop local estaba detenido; build e integración se ejecutaron en la VM existente. |
| 14. Costos y presupuestos | PARTIAL | Una VM, discos30+100 GiB,IP,buckets,registro,secretos y observabilidad existentes. Estimación **USD4.08/día;USD122.41/30d**,4.90/día con20% de reserva. Scratch dentro del disco/VM existentes; sin infraestructura facturable adicional. | Billing budgets403; factura y alerta presupuestaria no verificables. No es límite automático de gasto. |
| 15. Entrega y trazabilidad | PASS | Corregidos informe técnico, diagramas, matriz17 criterios, inventarios GCP, README y guion. Índice/huellas `summary.json`; cortes original171791, respaldo174607 y producción174734 diferenciados. | Sin ensayo oral cronometrado afirmado. |

## Porcentajes y alcance

- **Académico:17/17 =100%**, criterios funcionales/documentales de
  `docs/implementation/requirements.md`. Docker acredita builds controlados,
  no reconstrucción integral de una VM vacía ni reproducibilidad binaria.
- **Checklist cloud comparable con v1:13/15 =86.7%**, solo filas PASS;
  dos PARTIAL: activación nativa de healthchecks y presupuestos Billing.
  No significa preparación productiva ni conexión ChatGPT completada.

## Incidencias resueltas y pendientes externos

Se conservan los fallos iniciales: falta de `.dockerignore` en el bundle
(corregida y rebuild repetido), permisos del JUnit (corregidos, regresión
completa repetida), y arranque JVM sin hostname resoluble en red none
(corregido únicamente en scratch). El reintento desde GCS pasó en los tres
motores; los primeros FAIL no se reinterpretan como PASS.

Pendientes externos: **conectar y probar ChatGPT como dueño**, acceso IAM
Billing para presupuestos y factura. Activación de los cuatro checks Docker
nativos: diferida a una recreación autorizada; las sondas externas ya funcionan
y alimentan la métrica/alerta existente sin interrupción.

## URLs y veredicto

Dashboard público autenticado: https://ti-136-114-21-18.sslip.io/ · API:
https://ti-136-114-21-18.sslip.io/docs · MCP público OAuth:
https://ti-136-114-21-18.sslip.io/mcp · Airflow privado vía IAP:
http://127.0.0.1:18081/ .

**Listo para presentación académica: SÍ, con los límites declarados.**
**Conexión ChatGPT: servidor preparado y probado; cuenta aún pendiente.**
