# Ejecución Airflow 3.4 en GCP — corridas reales verificadas

Scheduler real (LocalExecutor, serie 1) en la VM `ti-dev-data`. Todas las
corridas ejecutadas con las bases cloud reales; ningún conteo es simulado.

## Última programada verificada en cierre v2 (11/11/2026)

`scheduled__2026-11-11T03:00:00+00:00`: SUCCESS,03:00:46–03:02:32 UTC,
105.84s,siete tareas SUCCESS/intento1. NVD2335 registros/2 páginas/0 retries:
127 nuevos/802 modificados/1406 unchanged por motor,174734 únicos y huella
`5d8d4de4...` igual en los tres. DAG finalmente ACTIVO. Durante restauraciones
aisladas se pausó temporalmente y se reanudó en finally; no se dispararon
sincronizaciones extra para el cierre. Evidencia `acceptance_v2/final_state.json`.

## Histórico de corridas verificadas del10/11 (orden cronológico)

| Run | Estado | Contenido verificado |
|---|---|---|
| `scheduled__2026-11-10T03:00:00+00:00` | 7/7 SUCCESS | Catch-up del schedule diario al despausar: **sincronización NVD API 2.0 real** — 5343 registros/3 páginas/0 reintentos, 2696 CVE nuevos → 174487 por motor, paridad `b1e91d5db6d56ab776b1deaa60a6751afa2483657ab92be225165ac791c6a335`; watermark avanzado tras verify |
| `full34_20261110T211553` | 7/7 SUCCESS, Neo4j try 2 | Replay idempotente full local: 171791 feeds, new=0 por motor, 2616 "stale" protegidos (sin regresión del contenido sincronizado), paridad `436cef47a29360f157c773cdd1e44b64b7c67e9909a5f5ee3f1fe2e2641a37ff` |
| `full34_20261110T212506` | 7/7 SUCCESS, Neo4j try 2 | Segundo replay full (duplicado accidental, ver incidencia): mismo comportamiento idempotente y paridad |
| `sync34_20261110T215555` | 7/7 SUCCESS | Sincronización manual etiquetada modo NVD: ventana 19:11→21:51, 2 páginas/2207 registros/0 reintentos, 120 CVE nuevos + 905 modificados + 1182 unchanged (solape idempotente) → **174607 por motor**, paridad `1f3fe1f5ed51962dca77b6d039f3d7f77eedd6c0fc8736e5f71883e1ac33facf`; DAG dejado ACTIVO |

## Diseño verificado en producción

- **Watermark solo tras paridad**: `nvd_sync.json` (volumen checkpoints)
  avanzó a through `2026-11-10T21:51:09Z` (committed 21:57:22) solo después
  de que `verify` confirmó conteos+huella iguales en los tres motores.
- **Idempotencia y solape**: la segunda sincronización re-procesó 1182
  registros del solape de ventana como "unchanged" sin duplicar
  (validate: 0 duplicados, 0 inválidos en ambas corridas).
- **Protección de regresión**: el replay de feeds anuales sobre datos ya
  sincronizados marcó 2616 registros como "stale" y no los sobrescribió con
  contenido más antiguo.
- **Reintento real**: `fail_neo4j_once` provocó UP_FOR_RETRY y éxito en
  intento 2 en ambas repeticiónes full (evidencia try_number=2).
- **Retry de conexión**: la corrida programada y los replays usan el mismo
  DAG de 7 tareas: extract→validate→3 cargas→kpis→verify.

## Cadencia diaria armada (estado final)

- DAG `nvd_threat_intelligence` **ACTIVO** (is_paused=False verificado),
  schedule `0 3 * * *`: sincronización NVD automática diaria.
- `ti-backup.timer` 02:00 UTC: respaldo frío coordinado antes de la
  sincronización (pausa el DAG y solo reanuda si estaba ACTIVO).
- `ti-health.timer` cada 5 min: telemetría a Monitoring/Logging.

## Incidencia registrada (corrida 2)

El relanzamiento de la repetición full mientras la primera aún ejecutaba
duplicó la corrida; el script de la primera pausó el DAG al terminar y las
cargas de la segunda quedaron en cola. Se despausó y se esperó su estado
terminal (`cloud_wait_run.py`): terminó 7/7 SUCCESS sin intervención en
datos. Ambas corridas son idempotentes; la paridad se mantuvo en todo
momento. Evidencia: `gcp_airflow_run2_completion.log`.

Evidencias: `gcp_sync34_run.log` (journal completo), manifiestos por run en
`data/staging/<sha256(run_id)[:20]>/run.json`, watermark del scheduler,
`airflow34_cloud_full_run1.json`, `gcp_airflow_cloud_replay.log`,
`gcp_airflow_run2_completion.log`.
