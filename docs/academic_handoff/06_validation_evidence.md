# 06 — Validación, resultados y evidencias

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](09_distributed_update.md).

## 6.1 Regla de lectura

Se distinguen tres niveles: **(a) código implementado** (existe en el repo),
**(b) funcionalidad probada** (evidencia automatizada con fecha), **(c)
evidencia histórica** (válida, de una fecha anterior — no presentar como
actual). No sumar suites repetidas ni convertir SKIP en PASS.

## 6.2 Resultados actuales (corte 16/11/2026)

### Volumen y paridad de motores
Escaneo completo de pares (cve_id, content_hash) en los TRES motores
(18:34 UTC, `technical_closure/runtime.json`):

| Motor | Registros | Duplicados | Huella SHA-256 (compartida) |
|---|---:|---:|---|
| MongoDB | 176.803 | 0 | `6f33b89a75265f6d56160e4f4c9fe64dd211b63b4971bfe2745dc4ed948bef8d` |
| Cassandra | 176.803 | 0 | idéntica |
| Neo4j | 176.803 | 0 | idéntica |

Método: lectura paginada de TODOS los IDs (no muestra, no COUNT frágil);
huella = Σ sha256(id:hash) mod 2^256, order-independent.

### Airflow
Versión 3.4.0; DAG activo; 0 import errors; **success=10 / failed=0**; 6 runs
programados consecutivos 11–16/11 con 7/7 tareas success cada uno; última
run 119s. Watermark `2026-11-16T02:55:08` comprometido tras verify.

### Última sincronización incremental (16/11 03:00)
Ventana 15/11 00:55 → 16/11 02:55 UTC; 1 página, **132 registros, 0
inválidos, 0 duplicados**; por motor: 112 nuevos / 10 modificados / 10
unchanged / written 122; as_of KPI 03:01:29.

### Dashboard
- **AppTest contra API real** (candidato y desplegado): 15/15 PASS — métricas
  vivas, filtros combinados, filtro contradictorio→0, warning en entrada
  inválida, snapshot Cassandra, rankings exactos, grafo 559 aristas únicas,
  filtro por tipo, readiness 3 motores, snapshot estable durante la suite.
- **Navegador Chrome autenticado por HTTPS** (agent-browser): 5 vistas, 0
  excepciones, 0 alerts; 2 gráficos Vega SVG en Overview; graphviz SVG;
  filtro exacto CVE-2024-0001 → "1 resultados"; página 3 del grafo → "59 de
  559 · Fin de resultados" (`technical_closure/dashboard_browser.json`).

### Pruebas automatizadas locales (16/11)
`pytest -q`: **94 passed / 8 skipped / 0 failed**. Los 8 SKIP son
integraciones opt-in de ESCRITURA (`tests/test_integration.py`,
`TI_INTEGRATION=1`) — no ejecutadas sobre producción por regla de la auditoría.
`ruff check src services tests airflow/dags scripts`: **0 errores**.
`uv lock --check` y `pip check`: PASS (73 paquetes).

### Terraform
`fmt -check` + `init -backend=false -lockfile=readonly` + `validate`:
**PASS** sobre export limpio del índice Git (sin state ni tfvars privados).
Sin apply. Módulo `modules/secrets` versionado (solo recursos, sin valores).

### Infraestructura
VM RUNNING; 13/13 contenedores healthy; discos 30+100GB con deletion
protection; buckets privados PAP enforced; firewall 80/443 público + 22 solo
IAP + puertos de BD solo entre tags internos; disco de datos 16/98 GB usado.

### Seguridad de repositorio
Escaneo del índice Git (JWT / private keys / tokens GitHub / claves Google):
**0 hallazgos**. Prueba automatizada de política `.gitignore`
(`tests/test_delivery_inputs.py`): rechaza secretos/state/tfvars/PPK/etc.,
acepta únicamente código `.tf` del módulo secrets.

## 6.3 Resultados históricos (válidos, con fecha — no presentar como actuales)

| Evidencia | Fecha | Resultado | Ruta |
|---|---|---|---|
| CRUD 3 motores | 11/11 02:37 | 12 PASS (C/R/U/D × 3), cleanup_verified | `docs/evidence/acceptance_v2/crud.json` |
| Restore aislado 3 motores (GCS privado, red none) | 11/11 05:21 | 3 PASS, 174.607 CVE huella exacta | `acceptance_v2/restore_three.json` |
| Suite cloud cierre v2 | 11/11 | 55 PASS/0 FAIL/0 SKIP (incl. 8 integraciones reales) | `acceptance_v2/cloud_tests.xml` |
| Replay full idempotente | 10/11 | 171.791 unchanged, written=0 × 3 motores | `docs/evidence/airflow34_full_manifest.json` |
| Retry real Airflow | 10/11 | load_neo4j success try_number=2 | `airflow34_scheduler_retry.json` |
| MCP suite SDK→HTTP producción | 11/11 | 63 checks PASS / 291 invocaciones | `codex_diagnosis/comprehensive_production.json` |
| MCP remediación integral | 11/11 | X01–X04 corregidos; 59 canary + 63 prod | `docs/integrations/mcp_comprehensive_remediation.md` |

## 6.4 MCP (funcionalidad ADICIONAL — valor agregado)

- **Estado actual**: confirmación MANUAL del dueño de uso exitoso desde
  **Codex App** (16/11) → `technical_closure/mcp_manual_confirmation.json`.
- **Base técnica**: 6 herramientas de solo lectura con contratos cerrados
  (inputSchema additionalProperties:false, outputSchema tipado), OAuth OIDC
  Keycloak PKCE S256, rechazo 401 sin/conn bearer inválido, discovery/JWKS 200.
- **Controles documentados**: recuperación de 559 relaciones sin duplicados
  vía MCP; catálogo 23.186 productos (corte 11/11: 23.186; 16/11: 23.258);
  aplicabilidad CPE con 396 ocurrencias y árbol booleano conservado.
- **Cómo hablarlo en la exposición**: "extensiones de IA sobre la misma API
  de solo lectura; no un requisito del curso". No prometer suite OAuth
  automatizada nueva (no se repitió por instrucción del dueño).

## 6.5 Controles documentales y sus límites

- Auditoría técnica completa: `docs/audits/technical_deliverables_audit.md`
  (7 PASS/3 PARTIAL el 16/11 mañana → **10/10 PASS** tras cierre, commit `6d947ce`).
- Limitaciones declaradas: sin HA; sin transacción distribuida; un escritor
  a la vez; cobertura NVD parcial; sin factura GCP (estimación USD ~4.08/día
  con SKU oficiales, histórico); restauración no reensayada tras 11/11;
  arranque en frío de la VM no ensayado (riesgo conocido, opcional).

## 6.6 Matriz de evidencias para informe y PPT

| Evidencia | Qué demuestra | Ruta existente | Cómo obtenerla de nuevo | Uso recomendado |
|---|---|---|---|---|
| Capturas 5 vistas dashboard (16/11) | UI real funcionando por HTTPS autenticado | `docs/evidence/technical_closure/screenshots/{overview,vulnerability_explorer,threat_analytics,graph_intelligence,data_pipeline}.png` | navegar + capturar; o re-ejecutar `closure_browser_validate.py` (requiere credencial web) | PPT principal + informe cap. resultados |
| runtime.json | Paridad 3 motores + 14 checks KPI + Airflow + contenedores | `docs/evidence/technical_closure/runtime.json` | re-ejecutar `closure_runtime_readonly.py` (lectura) | Informe: tabla de verificación |
| dashboard_browser.json | E2E navegador con DOM assertion por vista | `technical_closure/dashboard_browser.json` | ídem | Informe evidencia dashboard |
| dashboard_canary/deployed.json | 15 checks AppTest pre/post despliegue | `technical_closure/dashboard_{canary,deployed}.json` | `python scripts/verify_dashboard_readonly.py` con API_URL | Informe QA |
| terraform.json | fmt/init/validate en export Git | `technical_closure/terraform.json` | comandos del README Terraform | Informe infra |
| crud.json | CRUD real 3 motores (histórico 11/11) | `docs/evidence/acceptance_v2/crud.json` | `runner crud` (¡escribe! solo entorno autorizado) | Informe CRUD + demo en vivo si se aprueba |
| restore_three.json | Recuperación backup (histórico) | `acceptance_v2/restore_three.json` | NO repetir en vivo | Informe operación |
| airflow34_full_manifest.json | Idempotencia replay completo | `docs/evidence/airflow34_full_manifest.json` | no re-ejecutar (29 min) | Informe ETL |
| airflow34_scheduler_retry.json | Retry real Airflow | ídem | param fail_neo4j_once en entorno test | Informe ETL |
| gcp_dashboard_*.png (5, históricas 11/11) | Console GCP servicios | `docs/evidence/screenshots/` | consola GCP | PPT infra |
| mcp_comprehensive_remediation.md | Remediación MCP X01–X04 | `docs/integrations/` | — | Solo anexo valor agregado |
| Auditoría 10/10 | Estado final verificable | `docs/audits/technical_deliverables_audit.md` | — | Cierre del informe |
| kpis catalog | Definiciones/fórmulas | `docs/kpis/catalog.md` | — | Informe KPIs |
| Airflow UI grid (histórico) | DAG exitoso en UI | `docs/evidence/screenshots/gcp_airflow_ui_grid.png` | abrir UI vía túnel IAP 18081 | PPT pipeline |

**Prioridad de capturas para PPT** (claras, no redundantes):
1. overview.png · 2. graph_intelligence.png (SVG con paginación 59/559) ·
3. gcp_airflow_ui_grid.png · 4. una captura consola GCP (VM+discos) ·
5. tabla de paridad generada desde runtime.json (no imagen).
