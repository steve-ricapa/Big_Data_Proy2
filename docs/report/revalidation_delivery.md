# Entrega vigente — segunda revisión autónoma, 10/11/2026

## A. Estado general

**17/17 criterios funcionales/documentales locales implementados y verificados
(100% / 100%)**, denominador definido en `docs/implementation/requirements.md`.
No equivale a producción, certificación de seguridad, ensayo oral o despliegue
GCP. MCP es extra local implementado/verificado; ChatGPT remoto no conectado.

## B. Componentes funcionales y comprobación

- ETL streaming, normalización y checkpoints por motor, conservados/revalidados.
- MongoDB8.0.12,Cassandra4.1.9,Neo4j5.26.12, motores reales con datos persistentes.
- Airflow **3.4.0** slim recomendado: siete tareas, schedule diario y retry real;
  historial/volúmenes2.11 preservados/detenidos. No migración destructiva.
- API FastAPI y dashboard Streamlit cinco vistas; API Mongo read-only y consulta
  directa a Cassandra, más subgrafo Neo4j. No cifras ficticias ante fallos.
- MCP SDK/FastMCP stdio: seis herramientas de solo lectura por API, sin DB secrets.

## C. Pruebas y correcciones

**42pytest PASS,0FAIL,0SKIP en Docker**,35PASS/7SKIP Windows por aislamiento.
No sumar suites repetidas. Otras comprobaciones: cinco escenarios incrementales,
nueve checks KPI independientes,14HTTP,handshake/seis consultas MCP y rechazo
de entrada inválida. Airflow10000: siete SUCCESS,Neo4j intento2, dos runs reales.
Último `migration34_20261110T165908` ejecutado con Mongo writer readWrite.

Ensayo posterior full `full34_20261110T170841`:171791 entradas, siete SUCCESS,
Neo4j intento2,0escrituras/duplicados y paridad completa; ver sección D.
Cuatro filtros Explorer PASS; publicación/año medidos0.08/0.36s tras índices
frente a~5.5s previos, sin extrapolar a un benchmark universal.

Se corrigieron endpoints Docker sin IP/DNS recreando solo contenedores propios
sin borrar volúmenes; timeout Mongo vacío usando índice; fechas de calendario;
driver asyncpg Airflow3; auth file readonly y rutas MSYS; entorno de plugins
Docker en cliente MCP Windows. Detalles en `docs/implementation/revalidation.md`.

Auditorías pip-audit:145 paquetes instalados Airflow3,0 hallazgos conocidos;
63 paquetes de aplicación/MCP,0 hallazgos conocidos. No cubren OS/JVM ni todas
las configuraciones. La imagen2.11 vulnerable queda como referencia no recomendada.

## D. Datos

| Motor | CVE únicos presentes y verificados |
|---|---:|
| MongoDB |171791|
| Cassandra |171791|
| Neo4j |171791|

Paridad de todos los pares ID/hash confirmada por escaneo real. Tres JSON:
39369/45482/86940 entradas; tamaños/SHA256 originales nuevamente comprobados.
Carga inicial full previa por CLI compartida. **Airflow3 también pasó replay
full171791**: run `full34_20261110T170841`,siete SUCCESS/Neo4j intento2,
0 inválidos/duplicados,171791 unchanged y0escrituras por motor. Paridad final
de todos los IDs/hash. No confundir replay idempotente con carga en bases vacías.

## E. Infraestructura

Terraform fmt/init/validate/plan correctos, **37altas/0cambios/0bajas**.
ADC existente utilizado sin leer/imprimir credenciales. No apply/destroy,
APIs nuevas,subidas ni recursos cloud. Compose raíz/overlay, scripts Bash y
parser PowerShell correctos. No Git/commits/pushes; no se inicializa sin petición.

## F. Costos

Referencia académica mínima: aproximadamente **USD4.04/día,USD122.84/mes**,
us-central1,std4,discos y reserva auxiliar, mes730h, S/3.75/USD supuesto.
No factura ni cotización contractual. Mayor RAM ~USD220.67/mes; separación
parcial~USD246.67/mes. Supuestos/fuentes en `gcp_cost_estimate.md`.
No sumar escenarios antiguos720h con este730h. Reservar30% contingencia;
discos y objetos retenidos siguen costando con VM apagada. No autorización de gasto.

## G. Evidencias

- Estado: `docs/evidence/revalidation_state.json`, generado desde artefactos reales.
- Tests: `revalidation_integration_tests.xml/.log`, `revalidation_unit_tests.xml`.
- Dataset: `revalidation_inventory.json`; incremental: `revalidation_incremental.json`.
- KPI: `revalidation_kpi_audit.json`; HTTP: `http_validation.json`.
- Airflow: `airflow34_scheduler_retry.json`, logs y `airflow34_success.png`.
- Full Airflow: `airflow34_full.json`, `airflow34_full_manifest.json`,
  `airflow34_full_success.png`; replay real171791 sin duplicados.
- MCP: `mcp_validation.json/.log`; auditorías `airflow34_dependency_audit.json`
  y `mcp_dependency_audit.json`.
- Dashboard/Cassandra: `revalidation_dashboard_cassandra.png`.
- Terraform: `revalidation_terraform_init.txt`, `revalidation_terraform_plan.txt`;
  validate también repetido y PASS, comandos en README.
- Informe20secciones,guion24min,modelos,catálogo y checklist de capturas conservados.

## H. Pendientes exactos y límites

1. **Autorización externa**: GCP apply/APIs/recursos/subidas,Git remoto si se desea.
2. **Antes de producción/cloud**: TLS,auth Cassandra/RBAC,restricciones Neo4j
   Community,backups/restore,capacidad y aprovisionamiento/egress aprobados.
3. **Extra remoto**: ChatGPT requiere Streamable HTTP,HTTPS,OAuth y revisión;
   stdio local no lo sustituye.
4. Descargador NVD automático no implementado; incremental acepta feeds locales
   nuevos/modificados sin redescargar originales válidos.
5. Sin HA/transacción distribuida/concurrencia segura entre pipelines; cron
   yCLI deben coordinarse. CI preparado pero no ejecutado en plataforma remota.
6. Guion preparado,no ensayo oral cronometrado. No auditoría de seguridad externa.

No hay pendiente técnico de la migración Airflow local verificada; no presentar
estos límites productivos como funcionalidades ya implementadas.

## I. Demostración (PowerShell desde raíz)

```powershell
powershell -File scripts/start-local.ps1 -WithAirflow
docker compose run --rm --no-deps runner verify --run-dir data/staging/full_optimized
docker compose run --rm --no-deps runner crud --output docs/evidence/crud_demo.json
docker compose run --rm --no-deps runner selftest --output docs/evidence/incremental_demo.json
docker compose run --rm --no-deps tester -q -p no:cacheprovider
uv run --extra mcp python scripts/verify_mcp.py
```

Dashboard18501,API18000/docs,Airflow3 UI18081, todos127.0.0.1. DAG inicialmente
pausado. Ejecutar secuencialmente, nunca CRUD/CLI a la vez que DAG. Para ensayo
del scheduler usar comando `verify_scheduler3.py` del README, no repetir una
carga full durante la exposición. Apagar sin borrar: `scripts/stop-local.ps1`.
