# Entrega final cloud — Threat Intelligence Platform, 10-11/11/2026

> Cierre actualizado y límites verificados: [`final_acceptance_v2.md`](final_acceptance_v2.md).
> Los resultados previos de este documento se conservan con su fecha; no se
> suman a la nueva regresión cloud de 55 PASS.

Cierre del despliegue GCP autorizado (una VM, USD 5/día objetivo) sobre la
plataforma local ya revalidada. Toda afirmación de este documento cita
evidencia real ejecutada en `docs/evidence/`; nada se afirma por autorización
ni por existencia de archivos. URLs: dashboard/API
`https://ti-136-114-21-18.sslip.io` (Basic Auth), MCP
`https://ti-136-114-21-18.sslip.io/mcp` (OIDC), Airflow UI solo por túnel IAP
(`127.0.0.1:18081` de la VM, no publicado).

## A. Estado general

Despliegue **E2E real completado y verificado** en `proyectobigdata2-514216`:
una VM e2-standard-4 con 13 contenedores, HTTPS público con TLS 1.3, OIDC
Keycloak real, MCP remoto con seis herramientas de solo lectura,
sincronización NVD automática diaria verificada con CVE nuevos reales,
respaldo frío coordinado con subida privada a GCS y restauración aislada
verificada, observabilidad con 5 políticas de alerta. Pendientes externos: conexión
de la cuenta ChatGPT del dueño (paso manual documentado) y alertas
presupuestarias bloqueadas por IAM de facturación.

## B. Infraestructura y seguridad

- Terraform (puente ADC sin claves JSON): red + firewall solo 80/443, VM con
  discos 30+100 GiB `prevent_destroy`, buckets privados raw/processed,
  Secret Manager (10 recursos, sin texto plano en repo/logs), Artifact Registry
  con lector+escritor solo para la SA de la VM, 5 políticas de alerta.
  Plan final: **sin cambios ni deriva** (`gcp_final_plan_drift.txt`).
- Puertos de motores 27017/9042/7687 no publicados; admin Keycloak/master
  404 público; acceso operativo solo IAP SSH OS Login.
- Cassandra con usuarios de app (`ti_pipeline`/`ti_reader`), superusuario por
  defecto deshabilitado. Mongo con writer/reader separados.
- Imágenes durables publicadas en AR: `ti-app`, `ti-airflow`, `ti-mcp`
  (tags `20261110`/`latest`, catálogo verificado, `gcp_image_publish.json`).
- Persistencia de arranque: unidad systemd `ti-stack.service` habilitada;
  `ti-backup.timer` 02:00 UTC; `ti-health.timer` cada 5 min.

## C. Datos y sincronización NVD real

Carga inicial cloud desde GCS privado (SHA256 verificado): **171791 CVE por
motor** con huella idéntica a la local. La **corrida programada 03:00 UTC**
(catch-up al despausar) ejecutó la sincronización NVD API 2.0 real: 5343
registros en 3 páginas, 0 reintentos, 2696 CVE nuevos → **174487 por motor**
con paridad de huella en los tres. La sincronización manual etiquetada
`sync34_20261110T215555` (misma vía de código) añadió +120 CVE con solape
idempotente (1182 unchanged) → **estado final 174607 CVE por motor**, huella
`1f3fe1f5ed51962dca77b6d039f3d7f77eedd6c0fc8736e5f71883e1ac33facf` en los tres; watermark avanzado solo tras la paridad
(`nvd_sync.json`: through 2026-11-10T21:51:09Z, committed 21:57:22Z).
Entre la corrida programada y sync34, dos repeticiones full confirmaron new=0 por motor
y protección de 2616 registros más recientes como "stale" (sin regresión de
contenido). Evidencia: manifiestos por run en `data/staging/*/run.json`,
`gcp_airflow_execution.md`, `gcp_sync34_run.log`,
`gcp_database_validation.md`.

## D. Pruebas cloud

pytest en contenedor cloud: **53 passed** (`gcp_pytest.log`, CRUD real por
motor). HTTPS público: 14 checks PASS, incl. 401 sin auth, admin 404, TLS 1.3
válido hasta feb 2027 (`gcp_https_validation.json`). Protocolo MCP/OAuth
completo: PKCE S256 con login/consentimiento real del dueño, código rechazado
al reusarse, seis herramientas, identificador inválido rechazado
(`gcp_mcp_protocol_validation.json`). Detalle por área en
`gcp_e2e_tests.md`.

### Respaldo, restauración y evidencia visual

Respaldo frío `20261110T215846`: SUCCESS (21:58:51–22:01:50 UTC),
9 volúmenes; configuración y manifiesto incluidos en 11 objetos subidos al
bucket privado. Evidencia: `gcp_cloud_backup_validation.json` y
`gcp_cloud_backup_upload.json`. La subida registra SHA256 por objeto;
no constituye por sí sola una restauración desde GCS.

Primer ensayo histórico: restauración desde el archivo local de la VM a un volumen MongoDB
aislado, red `none`, fuente intacta: **174607 CVE**, huella idéntica a sync34
(22:09:13 UTC, `gcp_backup_restore_validation.json`). Esto valida recuperación
MongoDB; en ese corte no se ensayó Cassandra/Neo4j/Keycloak.
El cierre v2 sí restauró MongoDB/Cassandra/Neo4j desde nuevas descargas GCS
del respaldo11/11 02:00,174607 CVE y huella por motor; `acceptance_v2/restore_three.json`.
Cinco vistas del dashboard capturadas en `docs/evidence/screenshots/`.
La captura opcional de Airflow UI cloud no forma parte de los resultados
verificados; las corridas sí están acreditadas por estados y manifiestos.

Regresión local al cierre: **47 PASS / 8 SKIP** Windows, distinta de la
ejecución cloud previa de 53 PASS; no sumar ambas cifras.
Logs finales: `gcp_closure_local_pytest.log`, `gcp_closure_ruff.log`.
Comprobación operativa final (23:43 UTC): 13 servicios en ejecución,
healthchecks definidos en estado healthy, motores sin puertos publicados;
DAG `is_paused=False` (`gcp_final_services.txt`, `gcp_final_dag_state.txt`).
El CLI Airflow advierte que no puede importar graphviz para generar gráficos;
la lista de DAG y el estado activo sí se obtuvieron correctamente.

## E. Costos

Estimación con SKU oficiales (no factura): **USD 4.08/día, 4.90 con 20%**
de contingencia; preapply gate antes del apply (`gcp_preapply_cost_gate.json`,
`gcp_actual_costs.md`). Sin CloudRun/NAT/GKE/GPU/balanceadores. Alertas
presupuestarias: bloqueadas por IAM de facturación, documentadas para el
administrador (S/ 1000 créditos referenciales).

## F. Operación

- Acceso: `gcloud compute ssh ti-dev-data --tunnel-through-iap` (OS Login).
- Sincronización manual etiquetada: `sudo python3
  /opt/threat-intelligence/scripts/cloud_airflow_exec.py cloud_sync_run.py
  --label <etiqueta> --leave-unpaused`.
- Respaldo manual: `sudo systemctl start ti-backup.service` (o
  `cloud_backup.py` directo); restauración aislada verificada con
   `cloud_restore_three.py --gcs` (cierre v2, huella ligada al corte del respaldo).
- Cadencia diaria: respaldo 02:00 UTC → sincronización NVD 03:00 UTC
  (DAG `nvd_threat_intelligence` ACTIVO).

## G. Pendientes y límites

- Conexión de la cuenta ChatGPT: paso manual del dueño (pasos en
  `gcp_mcp_validation.md`); el servidor está verificado, la cuenta no se
  conecta sin login interactivo real.
- Alertas presupuestarias requieren `billing.budgets.*` (fuera de alcance).
- Académico: una VM, sin HA; TLS con hostname sslip.io (IP estable reservada);
  Airflow UI no pública; un pipeline a la vez por diseño.

Evidencia índice: `docs/evidence/gcp_*.json|log|md`. Estado local previo:
`revalidation_delivery.md`. Bitácora: `gcp_deployment.md`,
`cloud_execution.md`.
