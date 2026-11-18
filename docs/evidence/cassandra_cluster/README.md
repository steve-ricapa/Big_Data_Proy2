# Evidencia de la expansión Cassandra · 17–18 noviembre 2026 UTC

| Archivo | Qué acredita |
|---|---|
| `vms.csv` | Inventario Compute Engine: tres VMs y tres zonas. |
| `before.json` | Inventario original de las bases, esquema Cassandra, KPIs y dos CVE de control. |
| `after-cutover.json` | Inventario posterior a la migración, antes de actualizar desde NVD: 177.203 CVE por motor, cero duplicados y la misma huella completa que antes. |
| `airflow-etl.json` | Corrida incremental real: 7/7 tareas exitosas, 2.370 registros de NVD, 1.236 nuevos, 1.111 modificados y 23 sin cambios por motor. |
| `after-etl.json` | 178.439 CVE por motor, cero duplicados, huella común y snapshots MongoDB/Cassandra idénticos. |
| `dashboard-after-etl.json` | 15/15 comprobaciones en cinco vistas contra la API real tras la corrida incremental. |
| `quorum-repair.txt` | CQL identificó los tres hosts y RF=3. `nodetool repair --full --sequential` terminó para `system_auth` y `threat_intelligence` (48 rangos cada uno). |
| `failover-02.txt` | Nodo 2 `DN`; lectura/escritura con el cliente Airflow a `LOCAL_QUORUM`; dashboard AppTest contra API real; retorno a `UN`. |
| `failover-03.txt` | Nodo 3 `DN`; API devuelve el KPI real y las 15 comprobaciones del dashboard pasan durante la caída. Tras recuperar `UN`, lectura `ALL` y limpieza de las pruebas. |
| `nodetool-status.txt` | Salida de `nodetool status threat_intelligence` con los tres nodos `UN` y consistencia de aplicación observada. |
| `peer-02.txt`, `peer-03.txt` | Montaje ext4 persistente, política de reinicio y SSTable que contiene una partición histórica de control en cada peer. |
| `https-external.json` | Cliente externo por HTTPS con autenticación web; comprobaciones del dashboard, API y descubrimiento público OIDC. No equivale a iniciar sesión por MCP OAuth. |
| `mcp-stdio.json` | Handshake, listado y llamadas a los seis contratos reales con el SDK MCP, en el contenedor desplegado. No es la ruta HTTP OAuth de Codex. |
| `neo4j-relationship-crud.json` | Creación, lectura, actualización y eliminación de una relación aislada; limpieza de ambos nodos de prueba. |
| `crud.json` | Doce verificaciones CRUD contra las tres bases reales, con limpieza verificada. |
| `runtime.txt` | Contenedores de la VM principal, estado del anillo, compaction y temporizador de respaldo. |

Después de recuperar el nodo 2, se leyó la misma fila de prueba con `ALL` a las 23:58:59 UTC (mismo `writetime` `1794959756072000`, TTL restante 1.617 s) y se eliminaron condicionalmente las dos marcas de esa sesión, incluida la creada durante el fallo. Nunca se detuvieron ambos nodos a la vez.

**Respaldo previo:** snapshot `pre-cluster-20261117t233404`, configuración, esquema y archivo frío de Cassandra (192.160.224 bytes), restaurado en Docker sin red y sin montar el volumen de producción. La restauración devolvió 177.203 CVE únicos y la huella `30c92af4b219225bb80167f21580642dceaac2063b500f43f5a10808785a6998`, idénticas al inventario. El archivo se subió a GCS privado, se descargó desde GCS y su SHA-256 coincidió: `c2073d8b7b3f5211fb2af0176ee9a166997a9f780d313786435f7476d477393d`. No fue necesario crear un snapshot facturable del disco GCP. Por separado también se verificó una restauración aislada de los tres motores desde el respaldo GCS de las 02:01 UTC (176.803 CVE, otro corte).

**Pruebas locales:** 96 PASS, 8 opt-in SKIP, 0 FAIL; Ruff sin hallazgos. Estas pruebas no se confunden con las verificaciones contra producción. No se ejecutó una prueba de carga. El escaneo Cassandra del inventario tomó 6,151 s antes y 14,128 s después, incluyendo obtención de conexión, comprobaciones de esquema/KPI y lectura. Cambió la consistencia; no es una comparación controlada ni una predicción sobre la latencia de consultas puntuales. Las inserciones de prueba incluyen Paxos.

**Límites:** se reinició cada servicio Cassandra remoto como parte de su prueba de caída; no se reinició la VM principal ni se simuló la pérdida de dos nodos. La restauración aislada comprobada es la del respaldo anterior al cambio; no demuestra recuperación completa a partir de los respaldos futuros RF=3. El dashboard se verificó con el cliente HTTPS externo y con Streamlit AppTest contra la API real, no mediante una nueva grabación de navegador. El alcance de tolerancia a fallos es Cassandra, no toda la plataforma.
