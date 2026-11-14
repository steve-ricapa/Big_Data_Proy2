# Matriz vigente de cumplimiento — cierre v2, 11/11/2026

Denominador académico: **17 criterios originales**. No incluye la conexión
opcional del dueño a ChatGPT ni autoriza infraestructura nueva. Resultados
consolidados y porcentajes: `../report/final_acceptance_v2.md`.
`acceptance/` y `acceptance_v2/` se refieren a `docs/evidence/`.

| # | Criterio | Evidencia ejecutada / alcance |
|---|---|---|
| 1 | Dataset procesado | Feeds originales171791 entradas; corte cloud v2:174734 CVE por motor tras NVD API; `acceptance_v2/final_state.json`. No confundir inventario original con corte incremental. |
| 2 | MongoDB real | Escaneo completo,174734 únicos, índice único y huella; CRUD temporal cloud `acceptance_v2/crud.log`. |
| 3 | Cassandra real | SELECT paginado de cves_by_id, mismo total/huella; CRUD condicionado y limpieza verificada; proyecciones por consulta documentadas. |
| 4 | Neo4j real | 174734 CVE únicos y1488730 relaciones al cierre; subgrafo SVG real; CRUD con identidad temporal. |
| 5 | DAG de siete tareas | Airflow3.4.0 activo; última programada11/11 03:00:46–03:02:32 UTC,105.84s,7 SUCCESS; `acceptance_v2/final_state.json`. |
| 6 | Actualización incremental | Última:2335 procesados,127 nuevos/802 modificados/1406 unchanged por motor,0 duplicados; watermark tras verify. |
| 7 | CRUD de tres motores | **12 PASS cloud nuevos**, ID CVE-2099 temporal y cleanup_verified=true; `acceptance_v2/crud.log`; regresión integrada cloud. |
| 8 | Al menos cinco KPI correctos | **6 comprobaciones independientes PASS** (total, severidad, meses, Rejected, productos únicos, cambios30d); `acceptance_v2/quality.json`. |
| 9 | Dashboard real | Cinco vistas HTTPS, búsqueda/listado, snapshot Cassandra y SVG Neo4j; `acceptance_v2/browser.json`/screenshots y `http.json`. |
| 10 | Pruebas automatizadas | Nueva ejecución Windows47 PASS/8 SKIP; cloud55 PASS/0 FAIL/0 SKIP, incluido CRUD/permisos; `acceptance_v2/*tests.log`. No sumar ejecuciones. |
| 11 | Docker y reconstrucción | Cuatro imágenes app/test/MCP/Airflow construidas con etiquetas de verificación; Compose validado; `acceptance_v2/rebuild_retry.log`. No sustitución de imágenes productivas ni reconstrucción desde host vacío. |
| 12 | Terraform validado | Plan nuevo sin cambios (`acceptance_v2/terraform_plan.log`); infraestructura existente aplicada previamente. No apply/destroy en este cierre. |
| 13 | Costos con supuestos | Inventario API y SKU oficiales: USD4.0804/día, USD122.41/30d, no factura; presupuesto Billing403. `acceptance/prices.json`, `gcp_inventory.json`. |
| 14 | Informe técnico coherente | `technical_report.md`: distingue carga original/local, corte cloud, ensayos nuevos, reconstrucción parcial y pendientes externos. |
| 15 | Guion de exposición | `demo_script.md`: 24min, evidencia cloud y contingencias, sin pausar DAG cloud ni mostrar credenciales. No se afirma ensayo oral cronometrado. |
| 16 | Inventario de evidencias | Capturas y JSON/logs/huellas en acceptance_v2; `screenshot_checklist.md` distingue capturas reales e históricas. |
| 17 | Trazabilidad | Esta matriz enlaza resultados ejecutados con `final_acceptance_v2.md`, `progress.md` y `decisions.md`. |

## Fuera del denominador académico

- Cuenta ChatGPT: requiere conexión interactiva del dueño; servidor MCP/OIDC
  verificado con protocolo y seis herramientas, no conexión simulada.
- Billing: presupuestos/factura no accesibles por IAM; objetivo USD5/día no
  equivale a tope de gasto.
- No HA, certificación de seguridad, reconstrucción de VM desde cero ni
  reproducibilidad byte a byte de imágenes con tags de base no fijados por digest.
- Nueve healthchecks Docker activos; cuatro sondas externas periódicas. Los
  cuatro checks nativos nuevos están en Compose sin recreación inmediata.
- Restauraciones scratch de los tres motores: resultados exactos en
  `acceptance_v2/restore_three.json`; no declarar PASS si algún motor falla.
