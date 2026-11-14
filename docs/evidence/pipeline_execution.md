# Ejecución del pipeline

## Cierre completo verificado
**171791 CVE en cada motor**,0 inválidos/duplicados. `full_recovery.log`:huella común de todos los pares id/hash `1a60346f5dcdbe7ee928bc7a8cf22779abeeb2bdf23efa1f39f7c7c1c3c9fcd2`. Mongo159.686s y Neo4j304.868s son etapas concretas,no tiempo total. Cassandra escribió todos los lotes y falló en COUNT(*);recovery paginada100.27s,171791 unchanged/0 escrituras. Se conservan ambos logs. Manifiesto final `data/staging/full_optimized/run.json` tiene verify exitoso.

DAG1000 con dags test;DAG10000 con scheduler real `resilience_20261110T085141`:7 SUCCESS,Neo4j intento1 UP_FOR_RETRY por puerto deliberadamente cerrado,intento2 SUCCESS. scheduler_retry.json y airflow_retry_attempt=1.log/=2.log. UI muestra3 runs exitosos,incluida ejecución programada al habilitar. DAG pausado al terminar. Carga171791 fue CLI,no Airflow full.

## Historial de implementación y procedimiento
Las referencias a "en ejecución" o "actualizar" debajo describen el estado anterior al cierre;el resultado final es el del apartado precedente.

## Confirmadas
- `smoke100.log`:100 válidos,0 inválidos,100 por motor,KPI100. Verificación inicial solo conteos; reforzada luego a identidad/hash.
- `sample1000.log`:1000 entradas, reusa100 previos;1000 por motor y huellas iguales.
- `airflow_dag_test.log`:7 tareas reales con1000 entradas, estado final success; no afirmar disparo por cron.
- `incremental.log`:escenarios sobre CVE sintético aislado, eliminado después; no se suma al dataset.

## Carga completa
Primer intento SQLite en carpeta compartida Windows detenido para corregir latencia. Versión optimizada: SQLite temporal local, único upsert/fila, checkpoint volumen Docker `checkpoint_data`, progreso cada10000 registros. Fuentes originales intactas.

En ejecución: `docker compose run --rm --no-deps runner run --run-dir data/staging/full_optimized`. Evidencia `full_optimized.log`; manifiesto `data/staging/full_optimized/run.json`. Solo con `verify` exitoso afirmar carga completa/paridad; actualizar entonces.

## Recuperación
Si Cassandra falla, corregir y ejecutar `runner cassandra --run-dir <mismo run>`; después neo4j/kpis/verify. No repetir prepare ni borrar checkpoints. Ejecutar un pipeline por vez.

Para retry real scheduler disparar `{"limit":1000,"fail_neo4j_once":true}` tras concluir otra carga. Primer intento conecta a puerto Neo4j deliberadamente cerrado; marcador permite siguiente intento al puerto correcto. Inyección explícita de prueba, no fallo espontáneo; evidencia debe mostrar UP_FOR_RETRY y posterior éxito. Nunca habilitado por defecto.
# Actualización Airflow 3.4

Runtime recomendado: overlay `docker-compose.airflow3.yml`; metadata2.11
conservada/detenida. Dos ejecuciones reales del scheduler con10000 entradas y
siete tareas SUCCESS;última `migration34_20261110T165908` con usuario Mongo
writer readWrite. Inyección de fallo real Neo4j en intento1 y éxito en intento2.
`airflow34_scheduler_retry.json` y `airflow34_success.png` son evidencia vigente.

Ensayo full0 **SUCCESS**: `full34_20261110T170841` valida171791,0descartados/
duplicados,siete SUCCESS/Neo4j intento2;171791 unchanged,0escrituras por motor,
paridad final id/hash. `airflow34_full.json`, `airflow34_full_manifest.json` y
`airflow34_full_success.png`. Es replay completo, no carga en almacenes vacíos.
Estado estructurado en `revalidation_state.json`.

## Evidencias históricas conservadas
