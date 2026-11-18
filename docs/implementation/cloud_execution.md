# Ejecución autorizada cloud — 10/11/2026

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

Usuario autorizó APIs, apply, una VM, discos, transferencias y servicios
necesarios con objetivo máximo USD 5/día. No GPU/GKE/HA, destrucción de datos
ni recursos ajenos. No significa gasto bloqueado automáticamente.

| Etapa | Estado | Evidencia |
|---|---|---|
| Auditoría de punto de partida | Completa | 7 documentos obligatorios y Compose/DAG/código leídos |
| NVD automático | **Implementado y verificado en cloud** | API 2.0, ventanas 119 d, rate 6.2 s, retry acotado, watermark tras paridad; corrida programada real con 2696 CVE nuevos |
| Seguridad/backups | Cassandra auth, Mongo writer/reader, TLS 1.3, Basic Auth, OIDC; respaldo frío cloud + restauración aislada | `gcp_cassandra_users.log`, `gcp_https_validation.json`, `backup_local.py`/`cloud_backup.py` |
| Regresión | 53 pytest cloud PASS, 12 pruebas locales nuevas PASS, ruff PASS | `gcp_pytest.log`, `test_remote_mcp.py`, `test_sync.py` |
| Preflight cloud/costos | Gate 4.08 USD/día antes del apply | `gcp_preapply_cost_gate.json`, `gcp_official_skus.json` |
| Apply/carga/publicación/MCP remoto | **Completados y verificados** | Ver abajo |

## Bitácora de ejecución (todas las acciones reales)

1. APIs necesarias habilitadas manualmente; sin CloudRun API (no se usa).
   Preflight: imagen Debian READY, cuotas, SKU e2-standard-4 confirmado.
2. Terraform vía puente ADC (`terraform_adc.py`, token efímero solo en
   entorno hijo, sin claves JSON ni ADC alterado). Primer apply falló
   `invalid_grant`; corregido con el puente. Fix boot disk explícito
   (colisión de nombres). IP externa reservada estable para OAuth/DNS.
3. Observabilidad: 5 políticas de alerta + canal email (recuento API corregido el 11/11); telemetría con SA de
   VM; primer sample PASS.
4. Bootstrap VM: disco datos 100 GiB montado `/srv/ti-data`, docker data-root
   en él; código (bundle allowlist, SHA256) + dataset 1.12 GB desde GCS
   privado con verificación; secretos 0700/0444 sin texto plano.
5. Contenedores: 13 running; nueve con healthcheck Docker healthy y cuatro
   comprobados funcionalmente (no confundir ambos estados). OOM Mongo en carga inicial (157200) corregido
   con `mem_limit` 2g; reanudada desde checkpoints sin re-descarga. Carga
   completa verificada: 171791 por motor, huella igual a la local
   (`gcp_initial_load_recovery.log`).
6. Cassandra auth por API; usuarios writer/reader; superusuario por defecto
   deshabilitado. Keycloak 26.8.2 realm `ti` cliente `ti-chatgpt` PKCE S256;
   subject claim corregido por API admin.
7. Caddy público TLS 1.3 (válido hasta feb 2027) con Basic Auth
   dashboard/API; rutas admin Keycloak/master 404 (orden `route` del
   Caddyfile); descubrimiento OIDC RFC8414 y protected-resource 200.
8. Verificación externa completa: 14 checks HTTPS PASS
   (`gcp_https_validation.json`), protocolo MCP/OAuth completo PASS
   (`gcp_mcp_protocol_validation.json`), pytest cloud 53 PASS.
9. Despausado del DAG → catch-up de la corrida programada 03:00 UTC:
   sincronización NVD real (5343 registros, 3 páginas, 2696 CVE nuevos →
   174487 por motor con paridad; watermark avanzado tras verify).
10. Replay full idempotente `full34_20261110T211553`: 7 SUCCESS, Neo4j
    intento 2 real, new=0, 2616 stale protegidos, paridad mantenida
    (`airflow34_cloud_full_run1.json`, `gcp_airflow_cloud_replay.log`).
11. IAM `artifactregistry.writer` (repo único) aplicado; imágenes `ti-app`,
    `ti-airflow`, `ti-mcp` publicadas con tags `20261110`/`latest` y catálogo
    verificado (`gcp_image_publish.json`). Token de SA nunca persistido.
12. Unidades systemd: `ti-stack.service` habilitada, `ti-backup.timer`
    02:00 UTC activo, `ti-health.timer` 5 min activo.
13. Plan final Terraform: sin cambios ni deriva (`gcp_final_plan_drift.txt`).
14. Segunda repetición full `full34_20261110T212506` (duplicado accidental, ver
    incidencia): 7/7 SUCCESS tras despausar y esperar estado terminal. Sincronización
    etiquetada `sync34_20261110T215555` modo NVD con DAG dejado ACTIVO:
    2207 registros/2 páginas/0 reintentos, +120 CVE nuevos +905 modificados +
    1182 unchanged por solape → 174607 por motor con paridad, watermark
    through 21:51:09Z (`gcp_sync34_run.log`).
15. Respaldo frío SUCCESS (9 volúmenes + configuración + manifiesto, 11 objetos
    subidos a GCS). Restauración MongoDB aislada desde archivo local cloud:
    174607 CVE y huella idéntica a sync34, red none, fuente intacta.
    Cinco vistas dashboard capturadas y revisadas, incluida tabla de relaciones
    Neo4j. Evidencias `gcp_cloud_backup_validation.json`,
    `gcp_cloud_backup_upload.json`, `gcp_backup_restore_validation.json`,
    `gcp_dashboard_browser_validation.json`. DAG ACTIVO tras respaldo.
16. Regresión local final: 47 PASS / 8 SKIP Windows (integraciones requieren
    motores); ruff PASS. La ejecución cloud previa acreditó 53 PASS.

Límites del cierre: no restauración completa multimotor ni descarga/restore
desde GCS; captura opcional Airflow UI cloud no ejecutada. ChatGPT requiere
conexión manual del dueño y presupuestos Billing siguen bloqueados por IAM.

## Desviaciones e incidencias reales

- Budget alerts: `billing.budgets.*` denegado para ambas identidades;
  documentado para el administrador (no se tocaron permisos).
- OOM Mongo 1g→2g en la primera carga (sin cambio de costo; reanudado).
- El relanzamiento de la repetición full mientras la primera aún corría
  duplicó la corrida; la segunda quedó a la espera porque el script de la
  primera pausó el DAG al terminar. Corregido despausando y esperando el
  estado terminal; ambas corridas son idempotentes (new=0) y la paridad se
  mantuvo en todo momento. Registrado aquí por honestidad de bitácora.
- SSH sobre plink puede caer en corridas muy largas: se usan shells en
  segundo plano con timeouts generosos y wrappers sin pipes/comillas.

## Reglas respetadas

Nunca `terraform destroy` ni cambios en recursos con datos; sin borrar datos
locales; sin tocar recursos ajenos; sin exponer credenciales (verificaciones
por archivo, nunca impresas); un pipeline a la vez (respaldo pausa el DAG y
solo reanuda si estaba ACTIVO).
