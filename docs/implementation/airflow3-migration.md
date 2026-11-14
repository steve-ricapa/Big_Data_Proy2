# Migración local Airflow 3.4.0 — verificada

## Motivo y conservación

Airflow 2.11 y sus proveedores instalados reportaron 421 hallazgos conocidos
en 59 paquetes. No bastaba con aislar la UI. Se construyó una imagen slim
3.4.0 y un lock de dependencias mínimas con hashes. El DAG utiliza SDK 3 con
fallback para conservar la referencia 2.11, que **no es la opción recomendada**.

Se conservaron la imagen 2.11, su volumen de metadatos y logs, detenidos.
No se ejecutó migración in-place ni borrado de PostgreSQL anterior. La nueva
metadata usa `airflow3_postgres`; logs y auth tienen volúmenes separados.
Únicamente los checkpoints por motor son compartidos, para no reescribir datos.

## Ejecución real

`docs/evidence/airflow34_scheduler_retry.json`:

- Airflow 3.4.0, runs `migration34_20261110T164916` y
  `migration34_20261110T165908` (última con usuario Mongo writer).
- 10,000 entradas, siete tareas SUCCESS, task `load_neo4j` con try_number=2.
- Inyección deliberada de conexión a puerto Neo4j cerrado en el primer intento.
- Scheduler real, API de ejecución y procesador de DAGs separados.
- El DAG queda pausado al terminar; no dejar cargas programadas inesperadas.
- Además hubo run programado al despausar con límite predeterminado 1000.
  Además pasó el replay full `full34_20261110T170841` sobre171791 registros,
  siete SUCCESS/Neo4j intento2:0escrituras y171791 unchanged por motor,
  paridad completa al final. Carga inicial previa por CLI; no afirmar que el
  replay partió de bases vacías. Evidencia `airflow34_full_manifest.json`.

Auditoría final: **145 paquetes instalados, 0 hallazgos Python conocidos** en
`airflow34_dependency_audit.json`. No equivale a certificación de seguridad,
auditoría de OS/JVM ni ausencia de vulnerabilidades desconocidas.

## Problemas solucionados

1. `asyncpg` faltante: Airflow 3 necesita driver asíncrono para su API; añadido
   al lock y reconstruido, con `pip check` correcto.
2. SimpleAuthManager abre su archivo con `a+`; no puede utilizar un Docker
   secret readonly directamente. Entry point lo materializa sin imprimirlo
   en volumen privado, con umask 077, conservando contraseña existente.
3. Git Bash transforma argumentos `/opt/...` en rutas Windows. Los comandos
   de operación documentados son PowerShell; desde Bash usar
   `MSYS_NO_PATHCONV=1`. No confundir ese fallo de invocación con fallo del DAG.
4. Mínima RAM: LocalExecutor paralelo 1, API un worker, sin triggerer (no hay
   operadores deferrables), sin Celery ni Redis.

## Inicio reproducible (PowerShell)

```powershell
powershell -File scripts/start-local.ps1 -WithAirflow
# Solo Airflow 3, cuando motores y aplicación ya existen:
powershell -File scripts/start-airflow3.ps1
docker compose -f docker-compose.yml -f docker-compose.airflow3.yml exec -T airflow3-scheduler python /opt/project/scripts/verify_scheduler3.py
powershell -File scripts/stop-local.ps1
```

UI **http://127.0.0.1:18081**, admin y contraseña local privada en
`secrets/airflow-admin-password`. Nunca copiarla al informe/capturas.
SimpleAuthManager es apropiado para esta demostración local con operador de
confianza, no sustituto de SSO/autorización de producción. No exponer el puerto
externamente ni activar SimpleAuthManager all_admins.

Fuente oficial consultada: [Simple auth manager](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/auth-manager/simple/index.html),
documentación3.4.0 al consultar el10/11/2026: está destinado a desarrollo/pruebas;
producción exige controles adicionales. Se precarga un password privado para
evitar que la generación automática lo imprima en logs.

No usar `--remove-orphans` al ejecutar solamente el Compose raíz: los servicios
del overlay son parte intencional del mismo proyecto, no basura que borrar.
No ejecutar el DAG 2.11 y 3.4 simultáneamente ni mezclar pipelines CLI/Airflow.
