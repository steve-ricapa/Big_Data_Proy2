# Progreso vigente — 11/11/2026, cierre v2

**Despliegue GCP real completado y verificado** (autorizado: una VM, objetivo
USD 5/día). VM e2-standard-4 con 13 servicios running; nueve con healthcheck
Docker healthy y cuatro con sondas funcionales externas periódicas; HTTPS público TLS
1.3 con Basic Auth; OIDC Keycloak realm `ti` y MCP remoto verificado por
protocolo completo; **sincronización NVD automática diaria verificada con
CVE reales**: corrida programada 03:00 UTC (5343 registros, +2696 CVE) y
manual etiquetada `sync34` (+120 CVE, solape idempotente 1182 unchanged) →
174607 CVE por motor en ese corte. La programada11/11 03:00 UTC añadió127:
**174734 CVE únicos por motor con paridad de huella**, cero duplicados;
watermark avanzado solo tras
verify. Dos replays full cloud idempotentes (new=0, "stale" protegidos).
pytest cloud **55 PASS** nuevos; Windows47 PASS/8 SKIP; HTTPS y cinco vistas
reverificadas; MCP/OAuth PKCE y seis herramientas PASS.
Imágenes `ti-app`/`ti-airflow`/`ti-mcp` en Artifact Registry (catálogo
verificado); `ti-stack.service` (arranque), `ti-backup.timer` 02:00 UTC,
`ti-health.timer` 5 min. Plan final Terraform sin deriva. Respaldo frío
cloud SUCCESS; **restauración aislada desde GCS de tres motores PASS**:
174607 CVE del respaldo02:00 y huella igual a sync34 (previo a sync03:00).
Cinco capturas cloud revisadas, Graph con tabla de relaciones reales.
Cierre local: 47 PASS / 8 SKIP, ruff PASS. Estado operativo final:
13 servicios en ejecución y DAG ACTIVO (`acceptance_v2/final_state.json`).
Ver `gcp_e2e_tests.md`. Pendiente
externo: login manual ChatGPT del dueño y alertas presupuestarias (IAM).

Cierre local previo (histórico vigente): 17/17 criterios locales verificados;
42→53 pruebas Docker tras seguridad; Airflow 3.4.0; MCP local stdio; dataset
171791 con paridad; misma cifra era el estado cloud inicial antes de sincronizar.

| Tarea | Estado | Verificación |
|---|---|---|
| Infraestructura GCP | Completa | Terraform aplicado; plan final sin deriva |
| Contenedores cloud | 13 running; 9 healthy nativos + 4 sondas externas PASS | `acceptance_v2/component_health.log`; nativos nuevos declarados, sin recreación |
| Carga inicial cloud | 171791 por motor, huella igual a local | `gcp_initial_load_recovery.log` |
| Sincronización NVD cloud | Verificada real ×2 corridas | `gcp_airflow_execution.md`, `gcp_sync34_run.log` |
| Paridad post-sync | 174734 por motor | `acceptance_v2/final_state.json`: huella igual tres motores,0 duplicados |
| Seguridad cloud | Cassandra auth, TLS 1.3, admin 404, OIDC | `gcp_https_validation.json` |
| MCP remoto | Protocolo completo PASS | `gcp_mcp_protocol_validation.json` |
| Imágenes AR | Publicadas y verificadas | `gcp_image_publish.json` |
| Operación diaria | Armada | DAG ACTIVO 03:00 UTC, backup 02:00 UTC, health 5 min |

Cierre v2: CRUD temporal12 PASS con cleanup; cloud55 PASS, local47 PASS/8 SKIP;
cuatro builds Docker de verificación PASS, scripts/config/locks validados,
Terraform sin deriva. .dockerignore incluido y comprobado en bundle cloud.
Native healthchecks nuevos declarados para recreación autorizada futura;
cuatro sondas externas activas integradas a la alerta unhealthy_containers,
sin interrupción. Pendientes externos: ChatGPT y Billing IAM. Límites:
sin recreación de VM, host vacío ni garantía bit a bit.

## Histórico local anterior (conservado; sustituido por la fase cloud)

**Ensayo full terminado SUCCESS**: `full34_20261110T170841`,171791 registros
válidos,0 inválidos/duplicados,siete tareas SUCCESS,Neo4j intento2. Los tres
motores detectaron171791 unchanged,0escrituras y paridad final de IDs/hash.
Es un replay completo sobre almacenes existentes, no una carga inicial vacía.

| Tarea | Estado / archivos | Pruebas reales | Bloqueo / próxima acción |
|---|---|---|---|
| Auditoría/conservación | Completa, audit.md/revalidation.md | Código y entorno inspeccionados | Sin Git; no se publica |
| Dataset | Completo, revalidation_inventory.json | 171791 entradas, tamaños/SHA256 originales iguales | No redescargar |
| Tres motores | Verificados | 171791 CVE por motor; paridad completa id/hash | Escalado/HA no requeridos |
| ETL/incremental | Verificado con usuario writer | Cinco escenarios reales PASS; checkpoints por motor | Un pipeline a la vez |
| CRUD/permisos | Verificado, tests/test_integration.py | CRUD tres motores + Mongo reader no puede escribir | TLS/Cassandra auth antes de cloud |
| Airflow | **3.4.0 recomendado**, overlay aislado | Dos muestras10000 y replayfull171791; siete SUCCESS/Neo4j intento2; usuario writer | 2.11 conservado/detenido, no usar |
| Auditoría Python | Airflow145/MCP63 paquetes | 0 hallazgos conocidos en ambos alcances | No auditoría completa OS/JVM |
| API/dashboard | Verificados | 14 HTTP; snapshot Cassandra directo y captura PNG | Web solo loopback |
| MCP local | Implementado y verificado | Handshake,6 herramientas,6 consultas,entrada inválida rechazada | ChatGPT remoto/OAuth pendiente |
| Suite automatizada | **42 PASS Docker**,35PASS/7SKIP Windows | XML/log revalidation_*; ruff PASS | No sumar repeticiones como tests distintos |
| KPI | Verificado | Nueve checks independientes PASS tras Airflow3 | Catálogo/población/fecha explícitos |
| Terraform | fmt/init/validate/plan correctos | 37altas/0cambios/0bajas | Apply y recursos requieren aprobación |
| Docs/defensa | Actualizados | Informe20 secciones,guion24min,trazabilidad,capturas | Ensayo oral no realizado |

**17/17 criterios funcionales/documentales locales implementados y verificados
(100%/100%)**. MCP es extra verificado. No equivale a producción, ausencia total
de vulnerabilidades o despliegue cloud. Carga inicial full previa por CLI;
Airflow3 ejecutó muestras10000 y un replay completo171791 verificado.
Estado estructurado actual: `docs/evidence/revalidation_state.json`.

Pendientes externos: aprobación para GCP/APIs/subidas/recursos, Git remoto si
se desea y conexión remota ChatGPT con OAuth/HTTPS. Antes de producción: TLS,
Cassandra auth/RBAC, restricciones Neo4j Community, backups/restore y capacidad.
No bloqueo técnico pendiente de la migración Airflow local: ya pasó ejecución.

## Histórico anterior (conservado, sustituido por el estado vigente)

## Revisión autónoma posterior en curso
Ver `revalidation.md`: se conserva el trabajo existente; 37 pruebas reales
repetidas tras recuperar endpoints de red Docker sin borrar volúmenes;
paridad completa de 171791 CVE por motor y Terraform validate confirmados.
Se atienden rendimiento del conteo/API y migración de seguridad de Airflow.
El resumen histórico siguiente no acredita automáticamente cambios nuevos.

| Tarea | Estado | Verificación / próxima acción |
|---|---|---|
| Auditoría | Verificada | Archivos inspeccionados; no hay `.git`; Docker arrancado |
| Datos |Completo verificado |171791 únicos válidos,0 inválidos/duplicados,3 feeds/SHA256 |
| ETL/motores |Carga completa verificada |171791 CVE por motor,huellas id/hash iguales;full_recovery.log |
| DAG |7 tareas con1000/10000 |dags test1000 y scheduler10000 SUCCESS;Neo4j2 intentos |
| KPI/API/dashboard |Verificados |9 checks KPI independientes,12 HTTP,cinco vistas/PNG reales |
| Pruebas |37 pytest PASS Docker,0 FAIL/0 SKIP |Incluye6 integración;local31PASS/6SKIP,no sumar suites repetidas |
| Terraform/GCP |fmt/init/validate/plan verificados |37 altas,0 cambios/0 bajas;SIN apply |
| Docs/informe/guion/costos |Preparados/revisados |20 secciones,guion24min,modelos,KPI,costos,checklist/matriz |
| Integración local total |Verificada |delivery_state.json,integration_tests.xml,scheduler_retry.json |

**17/17 criterios funcionales/documentales locales implementados/verificados (100%/100%)** según requirements.md. **El proyecto no está cerrado en seguridad:** auditoría Airflow421 hallazgos/59 paquetes, pendiente técnico de migración;ver security_review.md. No significa producción/HA ni despliegue GCP. Guion preparado,no ensayo oral cronometrado. MCP opcional no implementado.

## Incidencias/operación
- Sin Git,commits/pushes;README inicial archivado. Secretos no mostrados;ADC/tokens no leídos.
- Otros contenedores Airflow intactos;puertos altos y límites RAM para este proyecto.
- Primer full SQLite bind Windows detenido por latencia,exit137 de parada no prueba OOM. Dedup temporal y checkpoint movidos a disco/volumen Docker;destino checkpoint previo preservado si existe.
- Cassandra confirmó todos los lotes pero COUNT(*) falló;recovery paginada detectó171791 unchanged/escritos0. Neo4j completó171791 y verify comparó todos los IDs/hashes.
- Scheduler `resilience_20261110T085141`:10000 entradas,7 SUCCESS,Neo4j2 intentos con UP_FOR_RETRY real. DAG pausado al terminar para evitar cargas inesperadas.
- Cinco vistas y Airflow UI capturadas;perfil temporal de auth navegador eliminado sin mostrar contraseña.

## Pendientes externos/opcionales
GCP apply,APIs,subidas/despliegue requieren autorización:no realizados. Pendiente técnico real:actualizar/migrar Airflow y dependencias auditadas,volver a verificar;no requiere permiso cloud. Antes de producción:TLS,auth Cassandra,mínimo privilegio Mongo,backups/restore/capacidad. Descargador automático NVD y MCP opcionales no implementados. CI preparado pero no ejecutado remotamente;sin Git/commits/pushes. API18000/dashboard18501 activos;Airflow18080 verificado pero servicios detenidos por seguridad,perfil opt-in orchestration. Sin puertos de motores.
