# Auditoría de aceptación — Big Data II / GCP

> Corte v1 conservado: sus PARTIAL describen la auditoría original, no el
> estado posterior. Cierre vigente: [`final_acceptance_v2.md`](final_acceptance_v2.md).

**11/11/2026, 00:27–00:39 UTC.** Comprobaciones nuevas; sin apply/destroy,
reinicios ni escrituras de datos de producción. Evidencias nuevas en
`docs/evidence/acceptance/` (nombres abreviados abajo). Restauración y CRUD
históricos se identifican expresamente; no se repitieron.

| Componente | Estado | Evidencia real | Pendiente |
|---|---|---|---|
| 1. GCP/Terraform | PASS | Inventario API: VM `ti-dev-data` RUNNING, e2-standard-4, discos 30+100 GiB, IP reservada, 2 buckets y 1 repositorio. `terraform_plan.log`: **No changes**. | Ninguno en infraestructura declarada. |
| 2. Docker | PARTIAL | `vm_probe.json`: **13 running; 9 healthy**: mongodb, cassandra, neo4j, api, dashboard, airflow3-api, airflow3-scheduler, airflow3-postgres, keycloak-db. | Sin healthcheck Docker: caddy, keycloak, mcp-remote, airflow3-dag-processor; comprobados por HTTPS/OAuth/MCP/heartbeat, no por estado running. |
| 3. MongoDB | PASS | Escaneo nuevo: **174607 únicos**, 0 duplicados; índice único CVE (`vm_probe.json`). | — |
| 4. Cassandra | PASS | SELECT paginado nuevo: **174607 únicos**, 0 duplicados; misma huella que MongoDB. | — |
| 5. Neo4j | PASS | Consulta nueva: **174607 CVE únicos**, 0 duplicados, **1488142 relaciones**; huella igual entre los tres motores. | — |
| 6. Airflow 3.4.0 | PASS | DAG activo. Última ejecución `sync34_20261110T215555`: 10/11, **21:56:08–21:57:22 UTC, 73,62 s**; extract, validate, tres cargas, calculate_kpis y verify: **7 SUCCESS**. Heartbeats scheduler/dag-processor healthy (`airflow_health.json`). | Triggerer ausente; este DAG no lo requiere. |
| 7. Incrementalidad | PASS | Manifiesto de esa sincronización releído: **2207 procesados; 120 nuevos, 905 modificados, 1182 unchanged por motor**; 0 duplicados. Escaneo actual confirma ausencia de IDs duplicados (`vm_probe.json`). | No se disparó otra sincronización. |
| 8. Dashboard | PASS | HTTPS 200 autenticado; Chrome: Overview, Explorer, Analytics, Graph y Pipeline con datos; grafo SVG renderizado (`browser.json`, `screenshots/`). | — |
| 9. API | PASS | `/health`, `/ready`, búsqueda/detalle CVE, rankings, snapshot Cassandra y relaciones: 200; total 174607 (`http.json`). | — |
| 10. MCP | PASS | OAuth/PKCE, rechazo de código reutilizado, initialize/list_tools y **6/6 herramientas** con respuestas reales (`mcp.json`). Sin token: acceso rechazado. | Conexión efectiva desde ChatGPT: **NOT VERIFIED**. |
| 11. Backups | PARTIAL | Último SUCCESS: **10/11 22:01:50 UTC**. 9 volúmenes + configuración/manifiesto; 11 objetos GCS con tamaños/metadatos SHA coincidentes; hash local Mongo recalculado. Restore histórico **22:09:13**, 174607 CVE/huella correcta (`vm_probe.json`, `summary.json`). | Sin nueva restauración ni recuperación multimotor desde GCS. |
| 12. Seguridad | PASS | TLS 1.3/certificado válido; 401 sin autenticación; admin Keycloak 404. BD sin puertos publicados y TCP 27017/9042/7687 inaccesibles. SSH solo IAP; directorio secretos 0700 y **31 montajes de secretos read-only** (`http.json`, `security_mounts.json`, `gcp_firewalls.json`). | Alcance limitado; no es pentest ni certificación. |
| 13. Tests | PARTIAL | Nuevos: **local 47 PASS/8 SKIP; cloud aislado 45 PASS/8 SKIP** (`local_tests.log`, `cloud_tests_retry.log`). Cloud sin red ni volúmenes de datos; consultas reales verificadas aparte. | Integraciones CRUD omitidas; 53 PASS cloud es evidencia anterior. Dos casos JWT adicionales solo locales. |
| 14. Costos/alertas | PARTIAL | Inventario facturable actual y SKU oficiales reconsultados (`gcp_inventory.json`, `prices.json`). **5 políticas Monitoring activas, 10 secretos**, no 7/9 como algunos reportes. | Presupuestos Billing: **403**, no verificables; factura real no obtenida. |
| 15. Entrega académica | PARTIAL | Informe, diagramas Mermaid, evidencias y guion presentes/revisados (`summary.json`). **6 KPI reconciliados independientemente** (`quality.json`). CRUD: artefacto histórico local, 12 PASS. | `system.md`/`requirements.md` y partes del informe contradicen el estado actual; CRUD y reconstrucción no reensayados. |

**A. Porcentaje de requisitos académicos verificados:** **13/17 = 76,5%**.
Matriz original; no cierro CRUD nuevo, reconstrucción reproducible, coherencia
del informe ni trazabilidad (criterios 7, 11, 14, 17; `academic_checks.json`).

**B. Porcentaje de despliegue cloud verificado:** **10/15 = 66,7%**.
Solo filas PASS de este checklist; PARTIAL no suma. No es porcentaje de código implementado.

**C. Bloqueos reales:** (1) conexión ChatGPT sin verificar; (2) IAM Billing impide
ver presupuestos; (3) documentación contradictoria; (4) cobertura incompleta de
healthchecks/integraciones; (5) recuperación multimotor desde GCS no ensayada.

**D. URLs operativas:** Dashboard **público autenticado**:
https://ti-136-114-21-18.sslip.io/ ; API **pública autenticada**:
https://ti-136-114-21-18.sslip.io/docs ; Airflow **privado, vía túnel IAP**:
http://127.0.0.1:18081/ ; MCP **público con OAuth**:
https://ti-136-114-21-18.sslip.io/mcp .

**E. Costo estimado:** **USD 4,08/día; USD 122,41/mes de 30 días**.
Con 20% de reserva: USD 4,90/día. Incluye VM/discos/IP y reservas para
GCS, registro, secretos, observabilidad y egreso; no factura ni tope automático.

**F. Veredicto final: PARCIALMENTE.** El núcleo funciona y permite una demo real
al profesor. Antes de una entrega sin reservas deben corregirse las
contradicciones documentales y explicitarse las coberturas pendientes.
MCP está técnicamente listo para intentar la conexión; solo un uso real desde
ChatGPT permitirá declararla completada.
