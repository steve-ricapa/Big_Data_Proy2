# Evidencias de cierre v2

Resultados nuevos de CRUD temporal, restauraciones aisladas, healthchecks,
validaciones no destructivas y regresión. No sustituir resultados históricos
ni afirmar reconstrucción de la VM o Terraform apply: no se ejecutan.

| Evidencia | Alcance |
|---|---|
| final_state.json | 174734 CVE por motor, paridad, último DAG exitoso y finalmente activo |
| crud.json / cloud_tests.xml | CRUD temporal con cleanup;55 tests cloud PASS |
| restore_three.json | Tres restores PASS desde descargas nuevas GCS del backup02:00 (174607 por motor) |
| restore_three_initial.json / restore_three_local.json | Fallos iniciales preservados y reintento local PASS; no confundir con ensayo GCS final |
| rebuild.json / build_*.log | Cuatro builds de verificación; sin sustitución productiva; límites expresos |
| input_validation.json / terraform_*.log | Scripts/Compose/lock y Terraform validados sin apply |
| component_health.json / monitoring_live.log | Cuatro sondas externas, métrica/alerta existente, no activación nativa por recreación |
| http.json / mcp.json / browser.json | HTTPS, seis herramientas y cinco vistas reales con SVG |
| summary.json | Validación cruzada de artefactos y huellas SHA256 |

Porcentajes:17/17 académico funcional/documental;13/15 checklist cloud con
PARTIAL para healthchecks nativos diferidos y presupuestos Billing.
Entrega: `docs/report/final_acceptance_v2.md`.
