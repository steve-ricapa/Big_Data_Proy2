# Despliegue GCP — bitácora real

> Bitácora de despliegue inicial; cierre vigente11/11/2026:
> `docs/report/final_acceptance_v2.md`. Nuevos CRUD cloud,55 tests cloud PASS,
> cuatro builds y restauración GCS de tres motores acreditados en acceptance_v2.

## Infraestructura
- Autorización explícita recibida: una VM, objetivo USD 5/día, sin destrucción de datos.
- APIs necesarias habilitadas; sin CloudRun API porque no se usa CloudRun.
- Preflight imagen Debian 12 READY, cuotas 200 CPU regionales/500 GiB SSD sin uso,
  SKU e2std4 confirmado 4 CPU/16 GiB, instancias previas 0.
- Plan inicial 41 altas/0 cambios/0 bajas, costo 4.08 USD/día y 4.90 con contingencia.
- Primer apply falló `invalid_grant` en provider google Go; Python ADC renueva correctamente.
  Bridge `terraform_adc.py` pasa token efímero solo al entorno, sin mostrar ni persistirlo.
- Apply con bridge creó recursos; VM falló por nombre boot implícito igual al data disk.
- Fix: disco `ti-dev-boot` explícito 30 GiB, sin cambiar 100 GiB de datos ni precio.
- IP externa reservada estable 136.114.21.18 (OAuth/DNS estables, `gcp_stable_ip_apply.log`).
- Observabilidad: 5 políticas de alerta + canal email (recuento API de `acceptance/gcp_inventory.json`; corrige la cifra anterior de 7).
- Registry: lector+escritor para la SA VM aplicados (`gcp_registry_writer_apply.log`, 1 added, 0 destroyed).

## VM y aplicaciones
- VM ti-dev-data RUNNING, IAP SSH real exitoso, 16 GB RAM, discos 30/100 GiB;
  datos montados en `/srv/ti-data`, docker data-root en el disco de datos.
- Dataset original subido a GCS privado; paquete código allowlist sin secretos/state
  (`gcp_source_bundle.json`, `gcp_dataset_upload.log`).
- Bootstrap: 13 contenedores running; nueve con healthcheck Docker healthy,
  cuatro sin check nativo entonces (`gcp_services_current.txt`). OOM Mongo en carga
  (157200) corregido con `mem_limit` 2g; reanudada desde checkpoints sin re-descarga.
- Carga completa verificada: 171791 CVE por motor, huella `1a60346f...c9fcd2` igual a
  la local (`gcp_initial_load_recovery.log`, `gcp_database_validation.md`).
- pytest cloud: 53 passed (`gcp_pytest.log`). Cassandra con usuarios de app, superusuario
  por defecto deshabilitado (`gcp_cassandra_users.log`).
- Keycloak 26.8.2 realm `ti`, cliente `ti-chatgpt` PKCE S256; subject claim corregido por
  API admin (`gcp_oidc_subject_configuration.json`).
- Caddy público: TLS 1.3 válido hasta feb 2027; Basic Auth en dashboard/API; admin
  Keycloak/master 404 (fijado orden `route` en Caddyfile); MCP OIDC verificado completo
  (`gcp_https_validation.json`, `gcp_mcp_protocol_validation.json`).
- Imágenes durables publicadas en AR `ti-dev-images`: `ti-app`, `ti-airflow`, `ti-mcp`
  tags `20261110`/`latest`, catálogo del registro verificado (`gcp_image_publish.json`).
- Unidades systemd: `ti-stack.service` habilitada (arranque), `ti-backup.timer` activo
  02:00 UTC, `ti-health.timer` cada 5 min. Telemetría primer sample PASS.
- Presupuesto Billing: BLOQUEADO por permisos (documentado en `gcp_actual_costs.md`).

## Cierre verificado
- Respaldo frío SUCCESS: 9 volúmenes, configuración y manifiesto; 11 objetos
  subidos a GCS privado (`gcp_cloud_backup_validation.json`,
  `gcp_cloud_backup_upload.json`).
- Restauración MongoDB aislada desde archivo local de la VM: 174607 CVE y
  huella igual a sync34, fuente intacta (`gcp_backup_restore_validation.json`).
  En ese primer ensayo no se probó descarga GCS ni restore de Cassandra/Neo4j.
  El cierre v2 sí lo ejecutó: tres PASS desde descarga privada GCS, sin fuentes productivas montadas.
- Cinco vistas cloud capturadas y revisadas; Graph incluye tabla de relaciones
  reales. Inventario: `gcp_dashboard_browser_validation.json`.
- DAG ACTIVO tras respaldo (is_paused=False); cadencia diaria conservada.

Ya completados tras la sincronización: corrida programada 03:00 UTC con
sincronización NVD real (+2696 CVE), dos replays full idempotentes (7/7
SUCCESS, Neo4j try 2) y sincronización etiquetada `sync34` (+120 CVE →
174607 por motor, DAG dejado ACTIVO). Detalle en `gcp_airflow_execution.md`.

Logs índice: `gcp_api_enablement.log`, `gcp_authorized_apply*.log`,
`gcp_bootdisk_fix_apply.log`, `gcp_first_ssh.log`, `gcp_vm_bootstrap*.log`,
`gcp_public_startup.log`, `gcp_initial_load*.log`, `gcp_pytest.log`,
`gcp_https_validation.json`, `gcp_mcp_protocol_validation.json`, `gcp_image_publish.json`.
