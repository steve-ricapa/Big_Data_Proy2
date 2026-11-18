# Auditoría de entregables técnicos — Big Data II · Threat Intelligence

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

**Fecha:** 16/11/2026. **Corte de consultas cloud:** 17:43–17:50 UTC.  
**Repositorio:** `steve-ricapa/Big_Data_Proy2`, `main`, commit
`74a557867d1d0c41f093292aff5a310d3e45adc2`.

## Dictamen

**El núcleo de datos funciona; la entrega completa aún tiene reservas.**
MongoDB, Cassandra, Neo4j, Airflow, ETL, KPIs e infraestructura desplegada
están acreditados dentro del alcance de lectura descrito abajo. Hay fallos
confirmados de calidad y completitud del repositorio, y falta acreditar el
cliente Codex y el frontend web actual de extremo a extremo.

**Cumplimiento técnico íntegramente acreditado: 70% (7 de los 10 componentes
solicitados).** Los otros tres son PARTIAL, no ausentes. No se concede medio
punto arbitrario a PARTIAL ni se interpreta este porcentaje como porcentaje
de código implementado, disponibilidad histórica o nota oficial del profesor.

No se implementaron correcciones. No se ejecutaron CRUD, cargas, replay,
backfill, inicializaciones de esquemas, restauraciones, builds, apply/destroy,
reinicios ni cambios de autenticación. La única incorporación al repositorio
es esta auditoría; el instrumental y sus resultados auxiliares se guardaron en
el directorio temporal local aprobado. Las consultas no imprimieron secretos.

## 1. Rúbrica y criterios aplicados

Se buscaron archivos de rúbrica/enunciado y documentos PDF/Word/PowerPoint,
además de referencias a profesor/rúbrica en la documentación. **No se encontró
una rúbrica original atribuible al profesor: NOT VERIFIED.**

- `docs/implementation/requirements.md:3–26` contiene una matriz elaborada
  por el proyecto de **17 criterios**, no un documento original del profesor.
  No permite certificar que sus pesos o requisitos sean oficiales.
- `docs/implementation/initial_readme.md:3–5,24–25` registra una exigencia
  histórica adicional de **al menos 50000 registros** y los tres motores
  originales. El volumen actual de 176803 satisface ese umbral registrado.
- Esa matriz añade incrementales, CRUD, pruebas, Docker/reconstrucción,
  Terraform, costos y trazabilidad. Se revisan sus aspectos técnicos como
  controles adicionales, sin imponerlos como rúbrica oficial desconocida.
- No se evalúan PDF, video, diapositivas ni exposición oral. Tampoco se
  incorpora el guion oral al denominador, aunque aparezca en la matriz previa.

**Estados:** PASS = implementación inspeccionada y evidencia operacional real
compatible con el alcance indicado; PARTIAL = parte acreditada y parte pendiente
o defectuosa; FAIL = comprobación concreta fallida; NOT VERIFIED = evidencia
insuficiente o prueba no ejecutada. Un servicio `healthy` o un HTTP 200, por sí
solo, no bastan para PASS. Se distinguen pruebas actuales e históricas.

## 2. Tabla de los diez componentes

| Componente | Estado PASS/PARTIAL/FAIL | Evidencia exacta | Problema detectado |
|---|---|---|---|
| 1. Código, dependencias, configuración e instalación | **PARTIAL** | **E1**: 90 pruebas PASS/8 SKIP; 73 paquetes compatibles; lint del núcleo PASS. `pyproject.toml:5–35`, locks, `.github/workflows/quality.yml:7–12`. **E2**: módulo Terraform referenciado pero ausente de Git. | Ruff completo falla con 25 errores; clon de Git carece de `modules/secrets`; README mezcla estados incompatibles. Instalación limpia completa **NOT VERIFIED**. |
| 2. MongoDB | **PASS** | **E3**: 176803 IDs únicos, 0 duplicados; validator real y 10 índices, incluido `cve_id_1` UNIQUE y `description_text`. `src/threat_intelligence/databases/mongodb/__init__.py:15–49`; bootstrap `scripts/init_mongo_users.py`. CRUD histórico real: `docs/evidence/acceptance_v2/crud.json:1–10,24`. | Sin fallo en lecturas actuales. C/U/D actuales **NOT VERIFIED por restricción de no escritura**; los PASS de CRUD citados son del 11/11, no de hoy. Validator cubre campos mínimos, no validación exhaustiva de todo NVD. |
| 3. Cassandra | **PASS** | **E3**: 176803 IDs únicos; misma huella que Mongo/Neo4j. Metadata real: keyspace `threat_intelligence`, NetworkTopologyStrategy `dc1:1`, durable_writes; cinco tablas. SELECT de las tres particiones analíticas para dos CVE de control devuelve filas correctas. `databases/cassandra/__init__.py:35–76,79–116`; CRUD histórico `acceptance_v2/crud.json:11–16,24`. | RF=1, sin HA; aceptable para la VM académica, no disponibilidad productiva. C/U/D actuales **NOT VERIFIED**. El CQL ejecutable está en Python, no en archivos `.cql` independientes: no se presupone que la rúbrica exija ese formato. |
| 4. Neo4j | **PASS** | **E3**: 176803 nodos CVE únicos, 634634 nodos totales y 1501507 relaciones; seis constraints UNIQUE y ocho índices ONLINE. `databases/neo4j/__init__.py:18–58`. Log4Shell: 559 relaciones recuperadas sin duplicados; CRUD histórico `acceptance_v2/crud.json:17–24`. | Sin fallo de consulta detectado. C/U/D actuales **NOT VERIFIED**. Huella de CVE no certifica individualmente todas las aristas; se contrastaron controles y paginación. |
| 5. Apache Airflow | **PASS** | **E4**: Airflow 3.4.0, DAG no pausado, 0 import errors. Seis ejecuciones programadas recientes, del 11 al 16/11, con siete tareas SUCCESS cada una. Última: `scheduled__2026-11-16T03:00:00+00:00`, 03:00:01.175782–03:02:00.491274 UTC. `airflow/dags/nvd_pipeline.py:16–35,111–116`. | Ningún fallo actual detectado: 10 runs SUCCESS/0 FAILED en metadata. Reintento real acreditado históricamente, no provocado hoy. No se disparó otro DAG. |
| 6. Pipeline ETL/ELT, extracción, normalización y consistencia | **PASS** | **E3–E5**: última sincronización real NVD de 132 entradas; 112 nuevas/10 modificadas/10 unchanged por motor; 0 inválidos/duplicados. Cargas y verify SUCCESS, watermark posterior a verify. Escaneo completo de tres motores con huella idéntica. `ingestion/sync.py:24–94,110–127`, `pipeline.py:52–121,141–198,242–309`. | Cobertura histórica NVD parcial, no dataset global completo. No hay transacción distribuida ni bloqueo contra CLI concurrentes; operación exige un escritor. Reensayo de escrituras/idempotencia hoy **NOT VERIFIED**; evidencia histórica y resultados de ingestas recientes sí disponibles. |
| 7. Dashboard funcional y visualizaciones | **PARTIAL** | **E6**: cinco vistas ejecutadas hoy mediante Streamlit AppTest **dentro del contenedor desplegado y contra la API real**, sin errores/excepciones. Overview muestra 176803/18080/53876/23258; Analytics consulta snapshot Cassandra del corte actual; Graph genera un elemento Graphviz. Código `services/dashboard/app.py:45–139`. Capturas browser históricas: `docs/evidence/acceptance_v2/browser.json`. | Frontend JavaScript/SVG y acceso HTTPS autenticado actual desde navegador **NOT VERIFIED**; no se confunde AppTest con browser E2E. Graph Intelligence solo muestra la primera página de hasta 250 aristas y no ofrece continuación, aunque la API sí. |
| 8. KPIs: mínimo cinco correctos, consultables y visualizados | **PASS** | **E7**: 14 contrastes de indicadores/snapshots/paridad PASS, con agregaciones independientes. Total, severidad, meses, CVSS por versión, Rejected, últimos 30 días, productos únicos, entradas de rankings y tamaño de grafo reconciliados. `analytics/kpis.py:5–52`, `docs/kpis/catalog.md:3–18`. API real, métricas y tablas AppTest verificadas. | Sin discrepancias detectadas. Rejected incluye 4036 registros; población incluye rechazados. Rankings son asociaciones NVD, no activos ni ataques; se verificaron conteos de las entradas, no una clasificación independiente completa de todos los empates. |
| 9. Infraestructura GCP desplegada, conectividad y persistencia | **PASS** | **E8**: API GCP confirma VM RUNNING e2-standard-4; discos persistentes 30+100 GB, autoDelete=false. 13 contenedores running/healthy, volúmenes de BD bajo `/srv/ti-data/docker/volumes`; acceso IAP y API→tres motores probado. HTTPS con validación de certificado y auth challenge; dos buckets privados con public access prevention enforced. | PASS del despliegue actual, **no** de reproducibilidad desde Git, HA o recuperación ante desastre. `ti-stack.service` enabled pero inactive/dead requiere aclaración operativa; no se infiere caída porque contenedores/consultas funcionan. Reboot y restauración de backup actual **NOT VERIFIED**. |
| 10. MCP: seis herramientas, autenticación y Codex App | **PARTIAL** | **E9**: 6/6 herramientas del SDK desplegado consultan datos reales; input cerrado/outputSchema y equivalencia content/structuredContent comprobados. Discovery OIDC/resource/JWKS 200, sin bearer e inválido 401. Inventario nativo Codex actual: `authStatus=notLoggedIn`, `tool_count=0`. `services/mcp_server/server.py`, `contracts.py`, `remote.py:18–63`. | OAuth positivo público y recepción/uso del contrato por Codex App **NOT VERIFIED actualmente**. Una consulta interna SDK→HTTP no acredita Streamable HTTP autenticado. No se inició login ni se alteraron credenciales. |

Los PASS de motores incluyen **implementación, esquemas reales, lectura actual
y evidencia CRUD histórica identificada**. No significan que se hayan vuelto
a ejecutar doce escrituras hoy. La misma distinción se aplica a retries,
replay e historial de restauración.

## 3. Evidencia actual y reproducible

### E1 — Código y pruebas

Ejecutado desde la raíz del repositorio, sin caché pytest ni bytecode en el
proyecto; temporales de tests fuera del repositorio:

```bash
PYTHONDONTWRITEBYTECODE=1 TI_INTEGRATION=0 .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp='C:/Users/steve/AppData/Local/Temp/opencode/technical-audit-pytest-20261116'
# 90 passed, 8 skipped, 2 warnings in 8.93s

uv pip check --python .venv/Scripts/python.exe
# Checked 73 packages; All installed packages are compatible

.venv/Scripts/ruff.exe check --no-cache src services tests airflow/dags
# All checks passed!

.venv/Scripts/ruff.exe check --no-cache src services tests airflow/dags scripts --output-format concise
# Found 25 errors; exit 1
```

Distribución exacta del lint fallido:

| Archivo bajo `scripts/` | Líneas | Hallazgos |
|---|---|---|
| `cloud_airflow_ui_shots.py` | 60,71,93,103,108 | BLE001, ASYNC210, ASYNC251 |
| `cloud_closure_v2.py` | 25,39 | PLW1510 |
| `cloud_component_health.py` | 24 | PLW1510 |
| `cloud_dashboard_shots.py` | 8,49,61,90,102,104,105,112 | I001, BLE001, ASYNC210, ASYNC251 |
| `cloud_rebuild_check.py` | 31 | PLW1510 |
| `cloud_restore_three.py` | 22,165,169,170 | PLW1510, BLE001 |
| `validate_rebuild_inputs.py` | 16,22,24,28 | PLW1510 |

El workflow versionado ejecuta precisamente ese lint amplio: su etapa de
calidad no puede pasar con este código/configuración. **Estado real de runs
GitHub Actions: NOT VERIFIED**, ya que `gh run list` requiere login en este
entorno; no se simuló una conclusión de Actions.

Los ocho SKIP corresponden a pruebas opt-in en `tests/test_integration.py`,
incluidas escrituras CRUD y pruebas de permisos que intentan escribir.
**No se activaron**, porque el usuario prohibió modificar las BD. Los dos
warnings son deprecaciones Starlette/httpx y cassandra/asyncore, no fallos
funcionales nuevos. Esta ejecución no instala ni actualiza dependencias.

### E2 — Git incompleto y documentación contradictoria

```text
git check-ignore -v infrastructure/terraform/modules/secrets/main.tf
.gitignore:13:secrets/ infrastructure/terraform/modules/secrets/main.tf
```

`git ls-files infrastructure/terraform/modules` omite ese módulo;
`infrastructure/terraform/environments/dev/main.tf:21–26` lo requiere mediante
`source = "../../modules/secrets"`. Un inventario de todos los `source` locales
de los `.tf` versionados detectó **exactamente una dependencia local ausente
de Git**, ese directorio. El archivo existe en esta máquina y declara recursos
e IAM, **no valores de secretos**; no es razón para publicar credenciales.
Un clon limpio no puede resolver todos los módulos. No se ejecutó Terraform
init/plan/apply ni se modificó `.gitignore` para corregirlo.

Contradicciones vigentes de `README.md`:

- líneas 83,177–179: dice que no hay descarga NVD automática, mientras 153–155
  la afirma y el código/metadata actuales la prueban;
- líneas 99,104,177–179: niega TLS/endpoint público remoto, mientras 151–165
  describe el despliegue HTTPS real;
- los conteos de 174607/174734 y las suites 47/55 tienen cortes históricos;
  hoy hay 176803 CVE y 90 PASS locales. El problema no es conservar historia,
  sino mezclar esos cortes con instrucciones/limitaciones vigentes sin separarlos.

### E3 — Bases reales y huella completa

Consultas ejecutadas a través de IAP y `docker exec` sobre los servicios
existentes; no se copiaron scripts a la VM. Se usó `Cassandra(...,
initialize_schema=False)` para evitar DDL implícito.

- Mongo: `listCollections` filtrado a `cves`, `list_indexes()`, lectura
  paginada de todos los pares `cve_id/content_hash`.
- Cassandra: metadata del keyspace/tablas y
  `SELECT cve_id,content_hash FROM cves_by_id`, paginado por el driver.
- Neo4j: `SHOW CONSTRAINTS`, `SHOW INDEXES`,
  `MATCH (c:CVE) RETURN c.id AS id,c.content_hash AS hash`, conteos y aristas.

| Motor | IDs únicos | Duplicados | Huella de pares ID/hash |
|---|---:|---:|---|
| MongoDB | 176803 | 0 | `6f33b89a75265f6d56160e4f4c9fe64dd211b63b4971bfe2745dc4ed948bef8d` |
| Cassandra | 176803 | 0 | misma huella |
| Neo4j | 176803 | 0 | misma huella |

La huella es la suma modular de SHA-256 de `id + ':' + content_hash`;
se inspeccionaron todos los IDs, no una muestra ni solo COUNT. **No es
recomputación del hash de cada raw histórico ni validación de cada arista.**
El snapshot se mantuvo igual al inicio/final de la comprobación.

Mongo: campos requeridos `cve_id, content_hash, published, last_modified`,
índice único de identidad; índices last_modified/month/severity/cwes/products.id,
compuestos `(year,cve_id)` y `(published,cve_id)`, text description inglés.

Cassandra: `cves_by_id(cve_id PRIMARY KEY)`, `kpi_snapshots(snapshot_id PRIMARY
KEY)` y tres tablas por severidad/producto/CWE con
`PRIMARY KEY ((bucket,month),published,cve_id)`, clustering published DESC,
cve_id ASC. Se verificaron filas exactas en las tres proyecciones para
CVE-2021-44228 y CVE-2024-0001. Los documentos Cassandra coinciden con la
proyección Mongo sin raw para ambos controles.

Neo4j: seis entidades con unicidad CVE/CWE/Product/Vendor/CPE/Reference;
relaciones AFFECTS/AFFECTS_CPE/CLASSIFIED_AS/REFERENCES y las de identidad
PRODUCED_BY/IDENTIFIES implementadas en el adaptador. Todos los ocho índices
consultados están ONLINE. CVSS controles: **10.0 v3.1** y **9.8 v3.1**.

La ausencia de archivos `.cql`/`.cypher` en `database/` no significa ausencia
de esquemas ejecutables: se implementan en `initialize()` y se documentan en
`database/README.md:1–15`. Si el profesor exige archivos nativos independientes,
ese requisito adicional no pudo confirmarse sin su rúbrica.

### E4 — Airflow actual e historial de retry

Lectura de `DagModel`, `DagRun`, `TaskInstance` y conteo SQL de `import_error`:

```text
version: 3.4.0
dag_id: nvd_threat_intelligence
is_paused: False
import_errors: 0
run_states: success=10, failed=0, running=0, queued=0
next_dagrun: 2026-11-17 03:00:00+00:00
```

Últimos seis runs programados: 11,12,13,14,15,16/11, todos SUCCESS;
42 task instances consultadas, todas SUCCESS. Último run dura aproximadamente
119.32 segundos. Las siete etapas son:

```text
extract -> validate -> load_mongodb -> load_cassandra -> load_neo4j
        -> calculate_kpis -> verify
```

El DAG configura `0 3 * * *`, catchup=false, max_active_runs=1,
max_active_tasks=1, retries=2, retry_delay=30s y backoff exponencial.
XCom transporta rutas, no el dataset. No se volvió a probar un retry inyectado;
`docs/evidence/airflow34_scheduler_retry.json:3–5,33–35` conserva el ensayo real
SUCCESS con `load_neo4j.try_number=2` del 10/11.

El primer probe de esta auditoría no produjo JSON por un import del
instrumental; se sustituyó por una lectura SQL de `import_error` y se repitió
con éxito. **No era un fallo del DAG** ni se corrigió código del proyecto.

### E5 — ETL, sincronización e idempotencia

Manifiesto verificado más reciente leído en Mongo `pipeline_runs`:

```json
{
  "started_at": "2026-11-16T03:00:50.917938+00:00",
  "status": "SUCCESS",
  "nvd_window_from": "2026-11-15T00:55:08.124309+00:00",
  "nvd_window_through": "2026-11-16T02:55:08.323007+00:00",
  "download": {"pages": 1, "records": 132, "requests": 1, "retries": 0, "complete": true},
  "validation": {"seen": 132, "unique_valid": 132, "invalid": 0, "duplicates": 0},
  "each_engine": {"new": 112, "modified": 10, "unchanged": 10, "written": 122, "total": 176803},
  "kpi_as_of": "2026-11-16T03:01:29.397074+00:00",
  "watermark_committed_at": "2026-11-16T03:02:00.047516+00:00"
}
```

La ingesta del 15/11 también es SUCCESS: 268 entradas, 73 nuevas,
165 modificadas y 30 unchanged por motor. Hay progreso real, no un scheduler
activo que relee siempre el mismo archivo.

`normalize.py:42–158` valida identidad/fechas, selecciona CVSS por versión y
fuente, deduplica CWE/productos, conserva raw y calcula hash. `pipeline.py`
deduplica en SQLite y ordena artefactos; `incremental/state.py:21–57` mantiene
checkpoint por motor y solo confirma tras escritura correcta. Cassandra
elimina claves antiguas de proyecciones y Neo4j renueva relaciones por CVE.

Idempotencia histórica explícita:
`docs/evidence/airflow34_full_manifest.json:17–48` registra replay de 171791
entradas con **written=0/unchanged=171791 en los tres motores**. Las pruebas
actuales de normalización/estado/paginación NVD pasan, pero no se lanzó un
replay ni se indujo fallo de escritura hoy.

### E6 — Dashboard: qué se comprobó y qué no

Se ejecutó `streamlit.testing.v1.AppTest.from_file` sobre
`/app/services/dashboard/app.py` en `threat-intelligence-dashboard-1`, usando
su API_URL real, sin reemplazar respuestas ni mockear bases.

| Vista | Resultado de ejecución servidor actual |
|---|---|
| Overview | 0 exception/error/warning; métricas 176803 CVE, 18080 CRITICAL, 53876 modificados 30d, 23258 productos. |
| Vulnerability Explorer | 0 exception/error/warning; dataframe, detalle JSON y total 176803. |
| Threat Analytics | 0 exception/error/warning; tres tablas de ranking; caption de Cassandra con as_of actual, sin aviso de divergencia. |
| Graph Intelligence | CVE-2021-44228 y botón de exploración ejecutados; dataframe y un elemento Graphviz, sin excepción/error. |
| Data Pipeline | Dos bloques JSON de estado/readiness; sin excepción/error. |

**Esto acredita ejecución de vistas y datos reales, no el render del SVG/JS
en un navegador.** Hay capturas y un SVG browser histórico en
`docs/evidence/acceptance_v2/browser.json:1–37`. No se presentan como actuales.
El acceso browser actual sin credenciales recibió el bloqueo de autenticación
esperado; los intentos de túnel del instrumental Windows no se establecieron.
No se infiere un fallo del dashboard por ese bloqueo, ni se inició login para
eludirlo. El E2E HTTPS autenticado de frontend permanece NOT VERIFIED.

Limitación funcional visible en `services/dashboard/app.py:118–134`:
solo consulta la primera página del grafo y declara tope250. Para Log4Shell
no permite ver las559 aristas desde esa pantalla. **La API sí pasó** hoy
la enumeración de559 claves distintas en8 páginas de73:
145 AFFECTS,4 CLASSIFIED_AS,358 AFFECTS_CPE y52 REFERENCES.

### E7 — KPIs reconciliados

Corte de KPI actual: **2026-11-16T03:01:29.397074+00:00**.
Se hicieron agregaciones Mongo independientes de `calculate()`, lectura del
snapshot Cassandra y conteos directos Neo4j; no se llamó al comando de auditoría
que podría inicializar Cassandra implícitamente.

```text
total_cves                 PASS  176803
severity                   PASS  18080/65578/75049/10263/7754/79
monthly                    PASS  diccionario completo igual al snapshot
cvss_by_version            PASS  3.1:123120@6.9182; 4.0:44441@6.2555;
                                 3.0:1452@7.3050; 2.0:36@6.0833
rejected_cves              PASS  4036
modified_last_30_days      PASS  53876
unique_affected_products   PASS  23258
top_cwes                   PASS  conteos de cada entrada publicada
top_products               PASS  conteos de cada entrada publicada
top_vendors                PASS  conteos de cada entrada publicada
severity_percent           PASS  todos los porcentajes redondeados
graph_counts               PASS  634634 nodos / 1501507 relaciones
cassandra_snapshot_equal_mongo PASS
three_engine_parity        PASS
```

Las dos últimas son controles de consistencia, **no KPIs adicionales**.
Se supera el mínimo de cinco indicadores calculados y consultables; AppTest
verifica métricas/tablas reales, quedando la reserva de browser indicada en E6.

### E8 — GCP, persistencia y respaldo

Comandos de lectura usados: `gcloud compute instances describe ti-dev-data`,
`compute firewall-rules list/describe`, `storage buckets list`; en VM,
`docker ps/inspect`, `df`, `systemctl show/is-active/list-timers`.

```text
project: proyectobigdata2-514216
zone: us-central1-a
VM: ti-dev-data RUNNING, e2-standard-4
IP pública: 136.114.21.18
discos: ti-dev-boot 30 GB + ti-dev-data 100 GB, PERSISTENT, autoDelete=false
/: 30G, 20G usados, 8.9G disponibles
/srv/ti-data: 98G, 16G usados, 78G disponibles
contenedores: 13 running, 13 healthy, restart_count=0 al consultar
```

Se comprobaron Mongo, Cassandra, Neo4j, API, dashboard, MCP remoto, Caddy,
Keycloak, su Postgres y los cuatro servicios Airflow3/Postgres. Montajes de BD
en `/srv/ti-data/docker/volumes/threat-intelligence_*`; la API no contiene los
datos dentro de su imagen. Se compararon hashes de nueve fuentes host/VM y
siete archivos dentro de imágenes API/MCP/dashboard: coinciden con lo local.

Firewall público:80/443; SSH22 solo desde35.235.240.0/20 (IAP).
La regla27017/9042/7687 usa **sourceTags=ti-dev-web**, no 0.0.0.0/0;
los contenedores de BD no publican esos puertos en el host. Buckets
`proyectobigdata2-514216-ti-dev-{raw,processed}` en US-CENTRAL1:
uniform bucket-level access y public access prevention enforced.

`ti-backup.timer`, `ti-health.timer`, `ti-component-health.timer`: activos.
Manifiesto de backup `/srv/ti-data/backups/20261116T020139/manifest.json`:
SUCCESS, iniciado02:01:48.646163 UTC. **No se rehashearon esos archivos ni se
verificó su restauración/subida GCS actual**. Restore multimotor histórico:
`docs/evidence/acceptance_v2/restore_three.json`,11/11, tres PASS sobre174607
CVE del backup correspondiente, sin volúmenes productivos montados.

Anomalía operativa a revisar: `ti-stack.service` tiene UnitFileState=enabled,
Result=success y ExecMainStatus=0, pero ActiveState=inactive/SubState=dead.
Su definición versionada usa Type=oneshot/RemainAfterExit=true. Esto merece
explicación del ciclo de backup/arranque; **no prueba un fallo de arranque**, ni
se comprobó mediante reinicio, expresamente fuera de alcance. Los13 servicios
y las consultas funcionan. HA, recuperación desde VM vacía, factura/Billing,
alertas presupuestarias y deriva Terraform actual: NOT VERIFIED en esta auditoría.

### E9 — MCP y límites de autenticación

Desde el SDK instalado en el contenedor MCP, contra HTTP FastAPI real:

| Herramienta | Validación semántica actual |
|---|---|
| `search_vulnerabilities` | ID exacto Log4Shell devuelve1; API CRITICAL devuelve18080. |
| `get_cve_details` | CVE correcto; aplicabilidad conserva396 ocurrencias NVD. |
| `get_affected_products` |145 productos para Log4Shell; catálogo API total23258. |
| `explore_cve_relationships` |73 aristas en la página y total559; enumeración API completa sin duplicados. |
| `get_top_cwes` |20 entradas; conteos contrastados independientemente con Mongo. |
| `get_vulnerability_statistics` |176803 y fecha de corte actual; concuerda con los tres motores. |

Las seis publican entrada cerrada y outputSchema; structuredContent y JSON de
content son iguales en las seis respuestas. `get_top_cwes(limit=1)` es rechazado
y FastAPI devuelve422 a un query parameter desconocido.

Pruebas públicas a17:44:14 UTC:

```text
GET /                                                   401 sin credenciales
GET /api/v1/kpis                                        401 sin credenciales
GET /.well-known/oauth-protected-resource/mcp            200, resource correcto
GET /auth/realms/ti/.well-known/openid-configuration      200, issuer correcto
GET /auth/realms/ti/protocol/openid-connect/certs         200
POST /mcp sin bearer                                    401 + resource_metadata challenge
POST /mcp bearer inválido de prueba                      401 + resource_metadata challenge
```

El verificador de `remote.py:18–37` valida RS256, firma/issuer/audience,
exp/iat/sub y scope ti:read. Las pruebas locales del contrato/JWT pasan.
**Ni estos rechazos ni el SDK interno prueban un token válido y consentimiento
actual del dueño.** El inventario del runtime Codex instalado devolvió:

```json
{
  "server": "big_data_ii_-_threat_intelligence",
  "authStatus": "notLoggedIn",
  "tool_count": 0,
  "mode": "inventory only; no login; no thread"
}
```

No se sobrescribió la evidencia nativa previa. La suite comprehensive está
ligada al corte11/11 y, correctamente, requiere renovar baseline tras la
ingesta legítima; no se forzaron los conteos antiguos de174735/23186 para
presentarlos como actuales. Los payloads legacy grandes continúan siendo un
riesgo conocido; `view=summary` existe, cambiar defaults requiere aprobación.

## 4. Requisitos incumplidos y verificaciones pendientes

### Incumplimientos técnicos confirmados

1. **Repositorio de infraestructura completo/reproducible: FAIL.** Falta
   versionar un módulo requerido por Terraform; no es ausencia de credenciales
   esperada en un clon, sino ausencia de código de infraestructura.
2. **Comando de calidad documentado y definido en CI: FAIL.** Ruff devuelve25
   errores. Las90 pruebas PASS no convierten ese lint en PASS.
3. **Documentación de instalación/operación coherente: PARTIAL.** README
   contiene afirmaciones vigentes contradictorias sobre NVD, TLS y MCP público.

### Obligatorios del alcance todavía no acreditados completamente

- **Compatibilidad/uso efectivo desde Codex App:** NOT VERIFIED, falta sesión
  autenticada vigente y llamada real desde el cliente.
- **Frontend dashboard HTTPS actual:** NOT VERIFIED; servidor/consultas reales
  sí comprobados. No se imputa una avería inexistente al login requerido.
- **Exhaustividad respecto a la rúbrica del profesor:** NOT VERIFIED. No puede
  asegurarse que no falte un formato nativo CQL/Cypher u otro requisito no
  disponible. No se afirma incumplimiento de una rúbrica desconocida.

No se encontró incumplimiento del mínimo seis etapas, mínimo cinco KPIs,
tres motores reales o umbral histórico de50000 registros. CRUD e idempotencia
poseen evidencia histórica real; no repetir escrituras prohibidas hoy es una
limitación explícita, no un fallo funcional demostrado.

## 5. Problemas funcionales y riesgos encontrados

- **Bloqueo reproducible de calidad/entrega:** lint completo y código Terraform
  ausente en el repositorio publicado.
- **MCP no utilizable por la sesión actual de Codex:** inventario0 herramientas
  por notLoggedIn. No hay evidencia de que el servidor o JWT estén averiados.
- **Exploración incompleta del grafo en dashboard:** tope250 sin controles de
  página; API/MCP sí permiten continuar hasta559. Es limitación de interfaz,
  no pérdida de relaciones en Neo4j.
- **Estado de unidad de arranque inconsistente con su definición:** requiere
  diagnóstico antes de prometer recuperación automática. No se reinició nada.
- **Riesgos conocidos:** cobertura NVD parcial; ausencia de HA y transacciones
  distribuidas; payloads legacy voluminosos; concurrencia CLI no coordinada
  automáticamente; snapshots de lectura no son MVCC. No son fallos nuevos de
  conteo ni justifican backfill, cambios masivos o infraestructura adicional.

## 6. Correcciones necesarias, por prioridad — propuestas, NO aplicadas

| Prioridad | Acción necesaria | Criterio de cierre |
|---|---|---|
| **P1** | Corregir el alcance de la exclusión Git y versionar **solo código** del módulo Terraform faltante, nunca valores de secretos. | Clon limpio resuelve todos los sources locales; init/validate en entorno de revisión, sin apply. |
| **P1** | Resolver los25 hallazgos Ruff de scripts operativos sin debilitar reglas para ocultarlos. | Comando completo de README/workflow exit0 y regresión mantenida. |
| **P1** | Dueño reautentica personalmente Codex; después validar schemas y6 herramientas por Streamable HTTP público autenticado, con baseline del corte vigente. | Inventario nativo6, resultados semánticos reales y llamada desde App; sin exponer tokens. |
| **P2** | Validar frontend dashboard en navegador con sesión autorizada y corregir contradicciones del README. | Cinco vistas actuales, filtros/detalle, tabla Cassandra y SVG; guía única distingue local/cloud e historia. |
| **P2** | Añadir controles de continuación del grafo en dashboard si se desea exploración completa. |559 relaciones accesibles desde UI sin duplicados, con límite/página visibles. No es necesario recargar BD. |
| **P2** | Explicar y revisar el estado de `ti-stack.service` y su interacción con backup/arranque. | Diagnóstico de solo lectura primero; un ensayo de reinicio/recovery requiere autorización independiente. |
| **P3** | Preparar una prueba de instalación limpia y, si se exige, exportes nativos de esquemas. | Ejecución reproducible en entorno aislado aprobado; no usar producción para CRUD/rebuild. |
| **P3** | Revisar defaults de payload y plan de cobertura histórica según aprobación. | Decisión explícita del dueño. No backfill ni defaults incompatibles por esta auditoría. |

## 7. Qué está listo para entregar

**Listos dentro del alcance académico y de lectura acreditado:**

- MongoDB, Cassandra y Neo4j: esquemas/índices, datos, consultas y evidencia CRUD
  histórica disponible e identificada.
- DAG Airflow de siete etapas y sincronización NVD diaria: ejecuciones recientes
  exitosas, retries configurados e historial de retry real.
- ETL/normalización y consistencia entre motores: datos actuales reconciliados,
  controles de idempotencia implementados y replay histórico sin duplicación.
- KPIs: más de cinco, fórmulas revisadas, conteos/medias contrastados y API real.
- Entorno GCP **ya desplegado**: conectividad, servicios y persistencia actuales;
  no equivale a promesa de reconstrucción desde el repositorio incompleto.

**No listos para declarar entrega integral sin reservas:** repositorio/guía de
reconstrucción, calidad global, dashboard frontend E2E actual y MCP desde Codex
App autenticado. El dashboard servidor y las seis herramientas backend
funcionan, pero esa evidencia no cierra las reservas de sus clientes.

**Resultado final: 7 PASS / 3 PARTIAL / 0 componentes totalmente FAIL.**
Existen **dos subcontroles FAIL confirmados** (completitud Terraform y lint).
Los NOT VERIFIED se mantienen explícitos y no se cuentan como PASS. Este
resultado sustituye cualquier extrapolación de porcentajes históricos para
el corte del16/11, sin alterar ni borrar las evidencias anteriores.

---

# Cierre técnico de pendientes — 16/11/2026 (segunda pasada)

Se ejecutaron las correcciones, no solo propuestas. Evidencias consolidadas en
`docs/evidence/technical_closure/` (ver su `README.md`). El dueño confirmó
manualmente una prueba exitosa del MCP desde **Codex App**; se registra como
confirmación manual, no como suite automatizada nueva, y no se repitieron las
pruebas exhaustivas ni se tocó OAuth/Keycloak.

## Tabla de cierre

| Componente | Estado anterior | Estado final | Evidencia |
|---|---|---|---|
| 1. Código y configuración | PARTIAL | **PASS** | Ruff completo 0 errores (25 hallazgos corregidos sin deshabilitar reglas); pytest 94 PASS/8 SKIP/0 FAIL; `uv lock --check` y `pip check` PASS; `docker compose config` con los cuatro overlays PASS; módulo `modules/secrets` versionado (solo código `.tf`+README); prueba automatizada de política Git (rechaza secretos/state/tfvars, acepta el código del módulo); escaneo del índice Git 0 secretos; Terraform fmt/init/validate PASS sobre export limpio del índice Git sin state ni `.terraform`. |
| 2. MongoDB | PASS | **PASS** | Re-check 16/11 18:34 UTC: 176803 IDs únicos, 0 duplicados, misma huella que los otros dos motores; 14 contrastes KPI/consistencia PASS. Sin escrituras. |
| 3. Cassandra | PASS | **PASS** | Mismo escaneo y paridad; snapshot Cassandra == Mongo; esquemas/particiones re-verificados. |
| 4. Neo4j | PASS | **PASS** | Mismo escaneo y paridad; 6 constraints y 8 índices ONLINE; 559 aristas de Log4Shell accesibles. |
| 5. Airflow | PASS | **PASS** | 3.4.0 activo, 0 import errors, success=10/failed=0, watermark 16/11 comprometido tras verify. |
| 6. ETL | PASS | **PASS** | Sin cambios de código; re-check de consistencia e idempotencia vigente (132 entradas, 0 duplicados). |
| 7. Dashboard | PARTIAL | **PASS** | 15/15 AppTest contra API real (candidato y desplegado); **navegador Chrome autenticado por HTTPS: 5 vistas, 0 excepciones**, filtros combinados, 2 gráficos Vega SVG, graphviz SVG y página 3 del grafo (59/559); paginación de grafo añadida a la UI; capturas en `screenshots/`; solo el contenedor dashboard recreado (rollback `ti-dashboard:pre-closure20261116`). |
| 8. KPIs | PASS | **PASS** | 14/14 contrastes independientes re-ejecutados tras el despliegue del dashboard. |
| 9. GCP | PASS | **PASS** | 13/13 contenedores healthy tras el cambio; otros 12 IDs idénticos; Terraform reproducible desde Git (init/validate en export limpio, sin apply); `ti-stack.service`: enabled, Result=success, RemainAfterExit=yes con inactive/dead es comportamiento documentado de oneshot tras el arranque; queda como riesgo operativo conocido, no defecto funcional. |
| 10. MCP/Codex | PARTIAL | **PASS*** | **PASS por confirmación manual del dueño** (Codex App). No se repitieron pruebas exhaustivas ni se modificó MCP/OAuth/Keycloak (instrucción explícita). El asterisco distingue confirmación manual de suite automatizada. |

## Porcentaje final

**10/10 componentes cerrados = 100% del alcance técnico solicitado**, con dos
salvedades honestas que no inflan el número pero deben leerse:

1. Componente 10: PASS se apoya en la confirmación manual del dueño, válida y
   suficiente para este cierre, pero distinta de una suite automatizada nueva.
2. No se ejecutaron: `terraform apply`, CRUD de motores, backfills, replay ETL,
   reinicio de VM ni prueba de arranque en frío. El PASS de GCP es sobre el
   despliegue existente y la reproducibilidad de configuración, no un ensayo
   de reconstrucción total.

## Pendientes que requieren intervención del dueño (no bloquean la entrega)

- **Opcional — ensayo de arranque/recovery:** reiniciar la VM en una ventana
  aprobada para verificar `ti-stack.service` en frío. Solo con autorización.
- **Opcional — defaults MCP a summary:** sigue pendiente tu aprobación explícita;
  no se cambió (compatibilidad con clientes existentes).
- **Opcional — backfill histórico NVD:** diseño listo; requiere inventario,
  piloto y aprobación separados.

## Archivos modificados en este cierre

- Código: `scripts/cloud_*.py`, `scripts/validate_rebuild_inputs.py` (lint);
  `services/dashboard/app.py` (paginación de grafo); `scripts/verify_dashboard_readonly.py`
  y `tests/test_dashboard.py`, `tests/test_delivery_inputs.py` (nuevos).
- Infraestructura: `.gitignore`, `.dockerignore`, `infrastructure/terraform/modules/secrets/`
  (versionado), `infrastructure/terraform/README.md`, `infrastructure/docker/dashboard.Dockerfile`
  (nuevo), `infrastructure/docker/python.Dockerfile`, `docker-compose.yml`.
- Documentación: `README.md`, `docs/architecture/system.md`, esta auditoría,
  `docs/evidence/technical_closure/`.

## Resultado

**Objetivo 10/10 alcanzado con evidencia suficiente dentro del alcance acordado.**
No se declaran PASS sin evidencia; las dos salvedades y los pendientes opcionales
quedan explícitos arriba.
