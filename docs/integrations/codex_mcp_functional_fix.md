# Big Data II MCP — corrección funcional y pruebas reales

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

> Fase posterior de contratos, versiones CPE, paginación y payloads:
> [`mcp_comprehensive_remediation.md`](mcp_comprehensive_remediation.md).
> Este documento conserva el corte funcional anterior.

**Corte: 11/11/2026,17:33–17:50 UTC.**

**Resultado técnico: PASS6/6 herramientas ejecutadas**, con sesión OAuth real
del dueño utilizada por el ejecutable nativo de Codex App0.167.0-alpha.4.1.
No se basa en `tools/list`: se verificaron respuestas, igualdad con NVD,
consultas directas a los tres motores y una auditoría independiente de KPI.
La repetición desde la conversación gráfica del dueño queda por confirmar.

## 1. Causa raíz y reproducción anterior a cambios

### A. Ausencia real de Log4Shell, no fallo OAuth

`CVE-2021-44228` **no existía en MongoDB, Cassandra ni Neo4j**. Las consultas
puntuales fueron realizadas con los clientes reales y credenciales internas
de lectura, sin abrir puertos de bases ni inicializar esquemas desde la API.

La carga base contenía feeds de publicación2024–2026 más las ventanas de
modificación incremental; **no es todo el histórico de NVD**. El registro
oficial recuperado tiene publicación2021-12-10 y última modificación
2026-08-11, fuera de la ventana reciente de sincronización. El año del ID no
define siempre el año de publicación, pero en este caso ambos son2021.

| Prueba real previa | Resultado |
|---|---|
| Mongo, `cve_id=CVE-2021-44228` | Ningún documento. |
| Cassandra, `cves_by_id` por PK | Ninguna fila. |
| Neo4j, `CVE.id` parametrizado | Ningún nodo. |
| API búsqueda exacta | HTTP200, `items=[]`, `total=0`. |
| API detalle | **HTTP404**, `detail="CVE not found"`. |
| API grafo | **HTTP404**, `detail="CVE not found in graph"`. |
| MCP detalle/grafo, autenticados | `isError=true`, mensaje genérico de API no disponible. |
| CVE control existente `CVE-2024-0001` | Detalle200, CVSS9.8, producto real y4 relaciones; mismo hash en los tres motores. |

El error interno preciso era `fastapi.HTTPException(404, ...)`, no una
excepción de conexión/query de Mongo/Cassandra/Neo4j. MCP capturaba cualquier
HTTPError bajo `RuntimeError("Vulnerability API unavailable or request rejected")`,
ocultando la diferencia entre un404 de cobertura y una avería.

### B. Filtros y semántica de productos incompletos

- La herramienta de búsqueda solo declaraba `cve_id`, `page` y `page_size`.
  No exponía palabra clave ni severidad. El cliente antiguo podía aceptar
  campos extra sin aplicarlos: las llamadas nativas de keyword/severity
  devolvieron erróneamente el total general174734.
- FastAPI ya filtraba severidad, pero **ignoraba `q`** porque no estaba
  declarado. La petición `q=log4j` no era búsqueda textual real.
- `get_affected_products()` devolvía exclusivamente el ranking global.
  Pasarle un CVE antes de la corrección no seleccionaba sus productos:
  devolvía los20 del ranking, algo distinto a lo solicitado.

No se encontraron errores de motores en el sondeo acotado previo. Los404
se observaron en API y MCP. Los desafíos401 de Caddy durante discovery son
esperados; no explicaban esas respuestas404 de las rutas internas.

## 2. Rutas HTTP y motores utilizados

MCP llama mediante GET a **`http://api:8000`**, dentro de Docker. No pasa por
Caddy ni requiere un segundo login OAuth para cada consulta interna. El
bearer se valida en el borde MCP; las bases usan las identidades configuradas.

| Herramienta | Ruta interna actual | Datos |
|---|---|---|
| `search_vulnerabilities` | `/api/v1/vulnerabilities?cve_id=...&q=...&severity=...&page=...&page_size=...` | MongoDB, filtros combinados con AND. |
| `get_cve_details` | `/api/v1/vulnerabilities/{cve_id}` | Mongo, documento canónico y `raw_cve`. |
| `get_top_cwes` | `/api/v1/cwes/top` | Snapshot KPI Mongo. |
| `get_vulnerability_statistics` | `/api/v1/kpis` | Snapshot KPI Mongo. |
| `get_affected_products(cve_id=...)` | `/api/v1/vulnerabilities/{cve_id}/products` | Productos y CPE del CVE en Mongo. |
| `get_affected_products()` sin ID | `/api/v1/products/top` | Ranking KPI global, compatibilidad conservada. |
| `explore_cve_relationships` | `/api/v1/graph/cve/{cve_id}` | Consulta Neo4j parametrizada. |

Cassandra conserva la copia canónica/proyecciones y el snapshot independiente;
no se inventa que cada herramienta la consulta cuando su ruta usa Mongo/Neo4j.

## 3. Cambios aplicados

### Código

| Archivo | Cambio |
|---|---|
| `services/mcp_server/server.py` | Keyword y severidad tipados; producto por CVE opcional; errores404/422/401/403 diferenciados sin cuerpos privados ni URLs internas. |
| `services/api/app.py` | `q` validado y búsqueda `$text`; endpoint de productos por CVE; validación de IDs en detalle/grafo; orden estable priorizando AFFECTS y conteo/truncación explícitos del grafo. |
| `src/threat_intelligence/databases/mongodb/__init__.py` | Índice nativo `description_text`, usado por búsqueda de palabras sin regex arbitraria ni escaneo literal no indexado. |
| `tests/test_api.py`, `tests/test_mcp.py` | Regresión de filtros combinados, productos, ausencia, parámetros y errores sanitizados. |
| `scripts/cloud_backfill_log4shell.py` | Operación puntual explícita, no una escritura disparada desde herramientas MCP. |

`keyword` de MCP se traduce a `q` en HTTP. Usa la semántica de búsqueda de
texto Mongo (términos/frases), no regex ni SQL/Cypher del usuario. Las
herramientas siguen siendo seis, de lectura y con paginación limitada.

El404 continúa siendo error correcto para un CVE realmente no cargado, pero
ahora explica cobertura limitada y distingue el fallo de OAuth. No se añadió
una descarga/escritura oculta al consultar un CVE desde MCP.

### Datos: únicamente el CVE requerido y sus proyecciones

Se descargó una respuesta real de:

`https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228`

La respuesta se archivó y pasó por **la misma normalización, cargas por motor,
checkpoints, cálculo KPI y verificación de paridad del proyecto**. Cada sink
registró `seen=1`, `new=1`, `written=1`, `modified=0`.

- JSON archivado SHA256:
  `58671756e1d6de00aac65a9dd316cd912976e2695adebe21083a2558701d180f`.
- Hash canónico:
  `f511cfc4077364e056813387ae2de7b08e8b43ee30f236eec0f46fd99a17aa18`.
- Sin duplicados añadidos ni actualización/borrado de otros CVE.
- Se añadieron las entidades/aristas del CVE y sus proyecciones de consulta;
  se recalcularon snapshots y se creó el índice textual necesario.
- Backup inactivo; DAG pausado durante la operación, sin runs queued/running.
  **DAG restaurado ACTIVO**; watermark NVD conservado byte a byte.

**El total correcto posterior es174735, no174734.** La diferencia es el único
CVE real incorporado para cumplir el caso solicitado, no una regresión ni una
cifra simulada. CRITICAL pasó de17894 a17895. Las restantes categorías de
severidad conservaron sus cantidades.

Los tres motores se escanearon completamente al finalizar. Todos tienen
174735 filas/nodos CVE y la misma huella de pares ID/hash:

```text
0bfda784bc4d093897e0e8423c092723091c6e73aeac0237b31fc02a332b3d64
```

La huella es exactamente la del último corte aceptado más la contribución
de este CVE. Sigue siendo una huella multiconjunto de hashes guardados, no
una auditoría de cada payload; para Log4Shell se verificó además el contenido
completo y todas sus asociaciones relevantes, no solamente su hash.

### Despliegue acotado

Se construyeron capas de aplicación con un contexto allowlist de código,
derivadas de las imágenes existentes, sin secretos/datos en el build.
Se actualizaron **solo los contenedores `api` y `mcp-remote`**.

- VM, discos, bases, Keycloak, Caddy y los otros11 contenedores conservaron IDs.
- Ninguna edición de OAuth, cliente, roles, realm, callback, scope o secretos.
- `services/mcp_server/remote.py` conservó su hash exacto de verificación JWT.
- No se modificó `C:\Users\steve\.codex\config.toml` en esta fase.
- Tags de release: `ti-app:functional20261111`, `ti-mcp:functional20261111`;
  aliases locales productivos actualizados. No se afirma publicación nueva en AR.
- Imágenes previas preservadas: `ti-app:pre-functional20261111` y
  `ti-mcp:pre-functional20261111`; fuentes previas conservadas en la VM.

## 4. Resultados E2E por herramienta

Se reutilizó la sesión guardada por el dueño mediante **el ejecutable real
de App**, JSON-RPC app-server y una conversación efímera sin turno de modelo.
El backend Codex realizó las llamadas MCP autenticadas, que atravesaron API y
bases reales. No se pasaron tokens al script ni se automatizó un nuevo login.

| Herramienta | Prueba real después de la corrección | Resultado |
|---|---|---|
| `search_vulnerabilities` | CVE exacto:1; keyword `log4j`:10; CRITICAL:17895; filtros combinados:1; combinación contradictoria y keyword inexistente:0. | **PASS** |
| `get_cve_details` | CVE-2021-44228 completo, igual al normalizado de la respuesta NVD capturada; control2024 sin cambios. | **PASS** |
| `get_top_cwes` |20 entradas, iguales al snapshot recalculado y auditado. | **PASS** |
| `get_vulnerability_statistics` |174735, snapshot `2026-11-11T17:42:23.986620+00:00`; coincide con auditoría independiente. | **PASS** |
| `get_affected_products` | Por CVE:145 productos y358 CPE, exactamente iguales a NVD normalizado; sin ID conserva ranking20. | **PASS** |
| `explore_cve_relationships` | CVE real en Neo4j;559 aristas salientes verificadas; API devuelve250, `total_relationships=559`, `truncated=true`, incluyendo Apache Log4j. | **PASS** |

Se validaron **14 llamadas nativas positivas**, más una negativa deliberada
de CVE inexistente que devuelve error404 explicativo. No se cuenta esta última
como fallo funcional ni se interpreta un HTTP200 de transporte MCP como éxito
si su contenido tiene `isError=true`.

### CVSS y relaciones verificables

- CVSS seleccionado de NVD: **3.1,10.0,CRITICAL**, fuente `nvd@nist.gov`.
- Vector: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`.
- Producto confirmado: identidad `["a","apache","log4j"]`.
- Neo4j: **145 AFFECTS,358 AFFECTS_CPE,4 CLASSIFIED_AS,52 REFERENCES**.
- Cassandra conserva el mismo documento canónico que Mongo sin `raw_cve`;
  su hash coincide. Mongo conserva el origen completo.

Los productos/CPE son asociaciones NVD; no prueban que cualquier versión de
un producto o un activo concreto sea vulnerable. Los límites de versiones y
condiciones AND/OR originales permanecen en
`get_cve_details.raw_cve.configurations`. No se reducen a un comodín CPE como
si fuese una afirmación de todas las versiones.

## 5. Regresión y evidencia

| Comprobación | Resultado |
|---|---|
| Pruebas locales completas | **55 PASS,8 SKIP**,0 FAIL. Skips de integración opt-in no se presentan como pruebas cloud. |
| Ruff de archivos productivos/tests modificados y backfill | PASS. |
| Ruff global `src services scripts tests airflow/dags` | **FAIL**,25 hallazgos en scripts operativos ajenos a esta corrección; no se editaron para ocultar el resultado. No se afirma lint limpio de todo el workspace. |
| Auditoría KPI independiente | **9 PASS**: total, severidad, meses, CVSS por versión, productos únicos, rankings CWE/productos, igualdad Cassandra/Mongo y conteos de grafo. |
| MCP sin bearer / con bearer inválido |401 esperado en ambos casos, con resource metadata correcto. |
| MCP con sesión OAuth real |14 llamadas funcionales correctas. |
| `/ready` |200, Mongo/Cassandra/Neo4j verificados. |
| Logs posteriores API/MCP/Caddy/motores | Sin etiquetas de excepción500/503/timeout/conectividad en el sondeo acotado. Los404 negativos y401 de desafío son esperados. |
| Scheduler final | DAG activo,0 runs activos; backup inactivo. |

Evidencias principales:

- `docs/evidence/codex_diagnosis/functional_before.json` y
  `functional_native_before.json`: fallos reales previos y controles.
- `docs/evidence/codex_functional/nvd_CVE-2021-44228.json`: fuente archivada.
- `stage_release.log`, `backfill_execution.log`, `activation.log`: compilación,
  carga1-CVE, huellas y alcance del despliegue.
- `backend_validation.log`: igualdad semántica de fuente, tres motores,
  conjuntos completos de productos/CPE y auditoría KPI.
- `docs/evidence/codex_diagnosis/functional_native_after.json`: respuestas
  auténticas por llamada, incluyendo errores negativos esperados.
- `docs/evidence/codex_functional/validation.json`: aserciones finales
  **PASS_TECHNICAL_FUNCTIONAL**; no es solo un inventario de herramientas.
- `local_tests.log`, `final_health.log`: regresión y cierre operativo.

Las evidencias contienen datos públicos NVD y estados sanitizados, no tokens
ni contraseñas. Los tests unitarios usan fakes declarados; las afirmaciones
productivas anteriores se basan en las ejecuciones reales separadas.

## 6. Volver a probar desde Codex App

1. Cierra y vuelve a abrir App y crea una conversación local nueva para cargar
   los **schemas de parámetros actualizados**. No recrees el MCP ni cambies OAuth.
2. Pide estas llamadas reales:

   ```text
   get_cve_details(cve_id="CVE-2021-44228")
   get_affected_products(cve_id="CVE-2021-44228")
   explore_cve_relationships(cve_id="CVE-2021-44228")
   search_vulnerabilities(keyword="log4j", severity="CRITICAL")
   ```

3. Espera CVSS10.0, Apache Log4j entre los productos, relaciones reales y
   resultados filtrados. Estadísticas generales deben reflejar174735.
4. Para repetir el E2E nativo sin GUI, desde la raíz del proyecto:

   ```powershell
   .\.venv\Scripts\python.exe docs\evidence\codex_diagnosis\discover_native_tools.py --binary app --functional-suite --evidence-name functional_native_after.json
   .\.venv\Scripts\python.exe docs\evidence\codex_functional\validate_results.py
   ```

Las aserciones están fechadas a este corte y fixture; si hay una sincronización
posterior que cambia cantidades, revisar esas expectativas, no falsificar los
resultados para conservar174735. La confirmación gráfica del dueño es una
evidencia adicional pendiente, distinta del E2E técnico ya ejecutado.

## 7. Límites y recuperación

- No se importó todo el histórico2021 ni todos los CVE ausentes. Otro ID no
  cargado debe producir404 explícito hasta una ingesta/backfill autorizado.
- La API de grafo mantiene límite250, ahora declarado; no se afirma que una
  respuesta contenga todas las559 aristas.
- No se hizo pentest ni restauración integral nueva en esta tarea.
- Rollback de código: retaggear las dos imágenes previas preservadas y
  actualizar solo API/MCP; restaurar únicamente las fuentes cambiadas desde
  `docs/evidence/codex_functional/previous_sources/` en la VM, tras comprobar
  que no haya trabajo posterior. No tocar OAuth ni otros contenedores.
- La carga de Log4Shell es dato NVD legítimo y consistente, **no un fixture
  temporal que deba borrarse**. Un rollback de datos requeriría autorización
  y coordinación separadas sobre tres motores, checkpoints y KPI; no se
  ejecutaron borrados para volver artificialmente al conteo anterior.

Referencia de fuente pública:
https://nvd.nist.gov/vuln/detail/CVE-2021-44228
