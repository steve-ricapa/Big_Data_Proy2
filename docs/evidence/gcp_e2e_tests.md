# Pruebas cloud — resultados reales ejecutados

| Comprobación | Resultado real |
|---|---|
| ADC renovación/lectura GCP | PASS |
| Imagen, región, SKU y cuotas | PASS |
| Terraform fmt/init/validate/plan | PASS |
| Apply (puente ADC, fix bootdisk, IP estable) | Infraestructura completa aplicada; plan final sin deriva |
| IAP SSH/VM 16GB/discos 30+100 | PASS |
| Presupuesto Billing | BLOQUEADO por permisos; documentado, no creado |
| Carga/tres motores cloud | PASS 171791 por motor, huella igual a local |
| pytest cloud en contenedor | **55 PASS** nuevos (`acceptance_v2/cloud_tests.log`); los53 anteriores son históricos |
| Corrida programada/sincronización NVD | PASS 5343 registros, +2696 CVE, paridad, watermark tras verify |
| Sincronización manual etiquetada sync34 | PASS 2207 registros, +120 CVE → 174607, paridad, DAG ACTIVO |
| Replay full idempotente ×2 | PASS 7/7, Neo4j try 2, new=0, stale protegidos |
| API/dashboard HTTPS | PASS 14 checks, TLS 1.3, 401 sin auth, admin 404 |
| MCP OIDC/HTTPS/seis herramientas | PASS completo, PKCE S256, replay rechazado |
| Imágenes AR publicadas | PASS 3 imágenes, catálogo verificado |
| Respaldo frío cloud + GCS privado | PASS 9 volúmenes + configuración + manifiesto, 11 objetos subidos (`gcp_cloud_backup_validation.json`, `gcp_cloud_backup_upload.json`) |
| Restauración aislada cloud | PASS MongoDB/Cassandra/Neo4j desde descarga GCS privada,174607 CVE y huella del respaldo02:00 en los tres; `acceptance_v2/restore_three.json` |
| Dashboard por navegador (5 vistas) | PASS cinco vistas revisadas y diagrama SVG Neo4j renderizado (`acceptance_v2/browser.json`, screenshots) |
| Restore aislado local Mongo | PASS histórico local 171791 y huella completa |

Regresión local de cierre: 47 PASS / 8 SKIP Windows (integraciones requieren
motores); nueva ejecución cloud completa: 55 PASS. No sumar ejecuciones distintas.
Ruff PASS. Cifras cloud de cierre v2:174734 CVE por motor tras
sincronizaciones reales. Evidencia índice: `gcp_airflow_execution.md`,
`gcp_database_validation.md`, `gcp_https_validation.json`,
`gcp_mcp_protocol_validation.json`, `gcp_sync34_run.log`.
