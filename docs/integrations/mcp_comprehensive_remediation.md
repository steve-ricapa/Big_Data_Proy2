# MCP Big Data II — remediación integral

## Línea base y alcance aprobado

Auditoría aportada por el dueño:100 casos inventariados,96 ejecutados
(84 llamadas MCP y12 validaciones cruzadas):77 PASS,4 FAIL,15 WARNING,
4 NOT TESTED adicionales. Snapshot `2026-11-11T17:42:23.986620+00:00`,174735 CVE.
Se reproducen las entradas concretas suministradas; no se inventan los
argumentos/IDs individuales de los otros casos no detallados.

## Propuesta de compatibilidad — registrada antes de implementar

- Conservar seis nombres, modos existentes y campos actuales de respuesta.
- Rechazar argumentos desconocidos, incluido `limit`: corrección explícitamente
  solicitada; llamadas que dependían de ignorar errores dejarán de aceptarse.
- Conservar `page="2"` de forma intencional y documentada; no aceptar booleanos
  o decimales como números de página. El JSON Schema describirá ambas entradas.
- Añadir paginación/filtros del grafo y un modo de catálogo global de productos,
  sin convertir silenciosamente el ranking20 existente en un catálogo completo.
- Exponer reglas CPE desde `raw_cve` en vistas de lectura. No migrar ni
  recalcular masivamente hashes históricos; no guardar límites específicos de
  un CVE en un nodo CPE global compartido por otros CVE.
- Añadir metadata y esquemas de salida; conservar JSON en `content` además de
  `structuredContent`, con equivalencia semántica verificada.
- Añadir `view="summary"`, proyección e `include_raw` opcional. **Cambiar el
  detalle por defecto para retirar `raw_cve` rompería clientes existentes**:
  se mantiene el modo legacy por defecto, a la espera de autorización para una
  migración de defaults. La reducción opt-in sí está dentro de esta intervención.
- No ejecutar backfill histórico. Presentar estrategia, estimaciones
  condicionadas a volumen medido, duración y riesgos para autorización separada.

## Bloqueo inicial de validación nativa

El11/11/2026 a las18:49 UTC el runtime real0.167.0-alpha.4.1 devolvió
`notLoggedIn`,0 herramientas y etiqueta `Token expired`. No se modificaron
credenciales ni se automatizó un login. Evidencia:
`docs/evidence/codex_diagnosis/comprehensive_baseline.json`.
El E2E OAuth nativo permanecerá pendiente mientras el dueño no renueve su sesión.

## Estado final de esta intervención

**Desplegado con validación de integración PASS; aceptación nativa OAuth
PENDIENTE.** Corte de comprobaciones11/11/2026,18:49–19:43 UTC.

-90 pruebas locales PASS,8 SKIP de integración opt-in,0 FAIL.
- Candidato:59 comprobaciones semánticas PASS sobre286 invocaciones SDK.
- Producción:63 comprobaciones semánticas PASS sobre291 invocaciones SDK.
- Esas invocaciones recorren **SDK MCP → HTTP FastAPI real → bases reales**.
  **No son291 llamadas HTTP Streamable autenticadas**: el acceso de operador
  al SDK interno no prueba OAuth ni reemplaza la prueba desde Codex.
- El runtime nativo sigue en `notLoggedIn`. El script nativo se detuvo con
  **`PENDING_USER_LOGIN`**, sin iniciar un flujo de autenticación ni consultar
  contraseñas. Por ello no se declara E2E OAuth completo ni éxito en la GUI.
- No hubo escrituras de CVE, migraciones, backfill ni cambios de credenciales.
  Se actualizaron solo los contenedores de aplicación API/MCP; los otros11,
  incluyendo bases, Caddy y Keycloak, conservaron sus IDs.

Los59/63 casos son conjuntos nuevos explícitos, no una reclasificación de los
96 originales. Hay solapamiento entre candidato, producción y unitarias:
**no se suman como pruebas distintas**. Los77 PASS originales se conservan
como resultado reportado por el dueño, no se atribuyen a ejecuciones nuestras
sin entradas individuales. Se repitieron todos los escenarios concretos de
X01–X04/W01–W09 y se añadieron pruebas de contrato, paginación y datos.

## Diagnóstico por FAIL y comparación antes/después

### X01 — Diferencia entre firma visible y esquema servido

La inspección anterior a cambios dentro del SDK de producción encontró los
cinco parámetros `cve_id`, `page`, `page_size`, `keyword`, `severity` en el
inputSchema de búsqueda. **El defecto de firma incompleta no se reprodujo en
ese esquema fresco**, aunque sí fue reportado en la vista de App. No se
presenta una hipótesis de caché/proyección del cliente como causa demostrada.

Sí se comprobaron problemas relacionados: ningún outputSchema y entrada
abierta por omisión. Ahora todos los contratos se generan explícitamente,
con límites publicados y `additionalProperties=false` en entradas. La firma
visible de App deberá verificarse después del login y una conversación nueva.

### X02 — Tipado insuficiente y modos confundibles

La respuesta anterior carecía de outputSchema. El registro de productos solo
tipaba `cve_id`; el cliente no podía distinguir el ranking de una lista completa.
Ahora hay inputSchema cerrado y outputSchema con `items`, `mode`, `cpes`,
`page`, `page_size`, `total` y metadata. Los productos son objetos tipados y
los rankings conservan pares `[identity,count]` para no romper clientes.

Modos actuales:

| Llamada | Semántica |
|---|---|
| `get_affected_products()` | Ranking global20 del snapshot; **no catálogo completo**. Metadata declara el límite y cómo continuar en modo catálogo. |
| `get_affected_products(cve_id=...)` | Productos del CVE y sus CPE, con restricciones por ocurrencia. Mantiene145/358 para Log4Shell. |
| `get_affected_products(mode="catalog", page=1, page_size=100)` | Catálogo global completo paginado; conteo por CVE distinto, orden estable. |

`page/page_size` solo son válidos en el catálogo global. Usarlos para simular
continuación del ranking20 o del modo por CVE devuelve error explícito.
`include_cpes` solo es válido con `cve_id`; `view` resumida se aplica al modo
por CVE. Estos controles evitan aceptar parámetros sin efecto real.

### X03 — Extra ignorado por el SDK

Causa confirmada: el modelo de argumentos generado por FastMCP usaba
`extra=ignore`. Python rechazaba ciertos kwargs directos, pero la validación
SDK los descartaba antes de invocar la función. Se reprodujeron todos los
ejemplos aportados, incluidos `limit="bad"` y extras en estadísticas.

Se registran herramientas `StrictTool` con modelos de entrada `extra=forbid`.
Los errores identifican campos/tipos, **sin reflejar valores de entrada**.
El rechazo sucede antes de HTTP. FastAPI también rechaza query parameters
desconocidos/duplicados; `limit` no se implementó ni se acepta en ningún modo.

### X04 — Proyección por identidad, no por aplicabilidad

La normalización guardaba CPE únicos por `criteria`, con `product_id`, y el
grafo compartía nodos CPE globales. Ese modelo de identidad no podía expresar
intervalos distintos de una misma CPE en diferentes CVE. En Log4Shell hay
**396 ocurrencias cpeMatch de origen, frente a358 identidades CPE normalizadas**.

La corrección es una **vista de lectura por CVE desde su `raw_cve`**, no una
migración masiva ni límites guardados en nodos globales compartidos:

- Conserva `versionStartIncluding`, `versionStartExcluding`,
  `versionEndIncluding`, `versionEndExcluding`, `vulnerable`, criterios y otros
  atributos originales, incluidos matches ambientales/no vulnerables.
- Cada ocurrencia tiene `source_path` y `logical_context` con los operadores
  AND/OR y `negate` realmente presentes. No se inventan operadores ausentes.
- `get_cve_details(include_applicability=true)` expone también el árbol exacto
  de `configurations`, fuente NVD y fecha de modificación del registro.
- `get_affected_products(cve_id=...)` incorpora `cpes[].constraints`.
- Las relaciones AFFECTS_CPE exponen reglas específicas del CVE. Las aristas
  AFFECTS referencian la aplicabilidad CPE; la identidad Product no afirma que
  todas sus versiones estén afectadas.

Las396 ocurrencias fueron comparadas contra sus JSON pointers originales,
campo por campo; el árbol devuelto coincide exactamente con NVD. Los hashes
canónicos almacenados no se cambiaron. **Cassandra y Neo4j siguen almacenando
identidades/proyecciones anteriores; las reglas completas son autoritativas
en Mongo raw y se unen en lectura.** No se afirma una migración de sus modelos.

| Defecto | Antes, reproducido | Después | Estado de cierre |
|---|---|---|---|
| X01 | SDK ya tenía keyword/severity; App reportaba firma reducida; outputSchema ausente | Esquemas completos, salida tipada y entrada cerrada verificados en SDK real | **SDK PASS; recepción/firma nativa PENDIENTE** |
| X02 | Respuesta sin esquema; ranking y productos difíciles de distinguir | Tres modos explícitos, ranking compatible y catálogo paginado | **PASS integración; nativo pendiente** |
| X03 | Los7 escenarios de extra/limit fueron aceptados e ignorados | Todos rechazados con errores específicos; inputs cerrados | **PASS integración; nativo pendiente** |
| X04 | CPE de dos campos; límites solo accesibles en raw | Árbol y396 ocurrencias expuestos; proyecciones CPE/grafo enriquecidas | **PASS datos/integración; nativo pendiente** |

## WARNING: tratamiento y resultados medidos

| Grupo | Corrección/comprobación | Resultado |
|---|---|---|
| W01 | Se conservó y documentó Mongo Text Search. `explain` parseó la cadena especial como términos `"'"` y `"_"`, sin frases ni términos negados;1630 coincidencias, no búsqueda literal completa. La estructura de consulta no procede del usuario. | **PASS semántica documentada**, no hallazgo de inyección ni pentest. |
| W02 | `page="2"` se conserva intencionalmente. Schema admite entero o cadena ASCII acotada; límites1–10000, page_size1–100, grafo1–250. Se rechazan bool, floats, negativos y cadenas fuera de rango. | **PASS**. |
| W03 | Metadata declara cobertura parcial, años observados y última ingesta verificada. CVE-2021-45046 permanece ausente: búsqueda0, detalle404. Sin descarga al consultar. | **WARNING de cobertura conservado**, no un falso dato completado. |
| W04 | Page/page_size, filtro de tipo, total filtrado y total de todas las aristas, has_more/next_page y relationship_key. | **PASS:559 aristas únicas en8 páginas de73**. |
| W05 | Ranking20 explícito y modo catalog separado. | **PASS:23186 identidades únicas en232 páginas**, recuento independiente coincidente. |
| W06 | Se preservaron descripción y límites. Se señala `description_mentions_excluded_boundary` para2.15.0 sin decidir automáticamente qué versión está afectada. | **WARNING de fuente intencional**, no se altera NVD para hacerlo desaparecer. |
| W07 | Vistas resumidas, proyecciones, raw opcional y JSON compacto; defaults legacy retenidos. | **PARTIAL: optimización opt-in PASS; cambio de default requiere autorización**. |
| W08 | as_of, población, fuente CVSS/vector, unidad y definición de rankings; definición explícita de rejected_cves. | **PASS integración**, rejected_cves4019 en este corte. |
| W09 | SDK devuelve CallToolResult con content JSON y structuredContent equivalentes, outputSchema validado. Ausencias opcionales no se insertan como null solo en un canal. | **PASS SDK/integración; cliente nativo pendiente**. |

La auditoría agrupa15 WARNING en estos9 temas; no se inventa una
correspondencia uno-a-uno con15 IDs individuales no proporcionados.

### Búsqueda y paginación

- Filtros externos `cve_id`, `severity`, `keyword`: **AND** entre ellos.
- Dentro de keyword: semántica nativa inglesa de MongoDB, términos positivos
  no citados OR, frases entre comillas y exclusiones con menos; no es regex
  ni substring literal. Se conservan los índices existentes.
- Orden de búsqueda `cve_id ASC`; páginas1–10000 y tamaño1–100. Se verificaron
  las dos páginas de5 para log4j:10 IDs ordenados, sin duplicados; página3 vacía
  con total10. Filtro contradictorio por CVE/severidad devuelve0, no se ignora.
- Catálogo: `cve_count DESC, id ASC`, caché de un corte por proceso; cuenta CVE
  distintos, no CPE/versiones. Ranking20 conserva los valores del snapshot.
- Grafo: prioridad AFFECTS,CLASSIFIED_AS,AFFECTS_CPE,REFERENCES, identidad destino
  y `elementId(r)` como desempate/relationship_key. Se verificaron repetición
  de página y cada filtro de tipo. Las559 aristas se descomponen145/4/358/52.
- Reutilizar `metadata.as_of` como `expected_as_of`: un corte distinto devuelve
 409 y obliga a reiniciar. `truncated` conserva su significado de respuesta
  parcial; para continuar usar **has_more/next_page**, no truncated.
- **No hay MVCC distribuido:** orden estable y guardia de corte no congelan
  escrituras durante una ETL antes de publicar KPI. No prometer un snapshot
  transaccional entre motores. Las enumeraciones completas se hicieron sin
  ETL/backup activo; ante ingesta o restauración se reinicia la enumeración.
  Los IDs internos Neo4j tampoco se prometen estables a través de restores.

### Payloads y decisión incompatible pendiente

Medición sobre datos reales: caracteres del JSON en content y bytes del
objeto de resultado MCP serializado, **sin cabeceras HTTP ni envelope RPC**.

| Operación | Content previo | Content actual | Objeto actual, ambos canales |
|---|---:|---:|---:|
| Búsqueda100, legacy |809565|575798|1254101 bytes|
| Búsqueda100, summary |—|70365|147287 bytes|
| Detalle Log4Shell, legacy |222106|160876|340884 bytes|
| Detalle Log4Shell, summary |—|3810|7952 bytes|

**No se vende la minificación de content como reducción del wire completo.**
Mantener texto para clientes antiguos y añadir structuredContent duplica datos;
legacy puede transmitir más que antes. Las vistas summary sí son pequeñas.
`description` resumida está limitada a512 caracteres y declara truncación.
Los campos de conteo sustituyen arrays grandes, sin inventar productos.

Contratos de optimización disponibles:

```text
search_vulnerabilities(keyword="log4j",severity="CRITICAL",view="summary")
search_vulnerabilities(view="summary",fields=["cvss","severity"],page_size=25)
get_cve_details(cve_id="CVE-2021-44228",view="summary")
get_cve_details(cve_id="CVE-2021-44228",include_raw=false)
get_cve_details(cve_id="CVE-2021-44228",view="summary",include_applicability=true)
get_affected_products(cve_id="CVE-2021-44228",view="summary")
```

La proyección solo admite campos de resumen publicados y conserva cve_id.
`fields` requiere view=summary. include_raw=true permite recuperar el origen
explícitamente. Productos summary conserva145 identidades y omite CPE salvo
include_cpes=true; metadata declara cpe_count358 y la omisión.

**Solicitud de aprobación:** cambiar defaults a summary/include_raw=false
para búsqueda/detalle y al modo pequeño por CVE. Antes se deben actualizar los
clientes que requieren arrays/raw a view=legacy/include_raw=true. No se aplicó
ese cambio incompatible, ni se eliminó content para consumidores antiguos.

## NOT TESTED originales y validaciones cruzadas

| Caso | Resultado de esta intervención |
|---|---|
| N01 original JSON Schema | **PASS inspección SDK de producción antes/después**. Recepción por runtime nativo y firma GUI: **NOT TESTED, sesión expirada**. |
| N02 todas las relaciones | **PASS**:559 claves distintas,8 páginas, distribución completa y filtros. |
| N03 motores directos | **PASS**: escaneo completo de ID/hash de Mongo/Cassandra/Neo4j, controles CVSS y documento Cassandra/Mongo. |
| N04 catálogo independiente | **PASS**:23186 productos, digest de IDs/conteos idéntico al agregado Mongo alternativo con addToSet(CVE ID). |

Hash del catálogo enumerado, ordenando pares `[product_id,cve_count]`:
`f2bb985fab77046500d8d0cf9d22633b0d6b7bf3d8b91dc0ffe625dcb7fd6720`.

Los tres motores antes y después mantienen174735 CVE,0 IDs duplicados y:
`0bfda784bc4d093897e0e8423c092723091c6e73aeac0237b31fc02a332b3d64`.
Snapshot y severidades permanecen exactamente en la línea base aportada:
17895/64615/74203/10115/7828/79. Se mantuvieron CVSS10.0 y9.8 para los dos
controles y la igualdad del snapshot Cassandra/Mongo. La huella usa hashes
guardados; no se presenta como reserialización de todos los payloads históricos.

El catálogo alternativo y los controles por CVE sí contrastan datos reales,
no solo contadores. No se ejecutó CRUD ni se borraron fixtures productivos.
Las8 integraciones opt-in omitidas en pytest no se declaran PASS; las pruebas
de lectura en bases reales y la integración HTTP se documentan por separado.

## Cobertura observada y estrategia de backfill — NO ejecutada

Conteos por **año de publicación**, no por año del identificador CVE:

| Año | Cargados observados |
|---|---:|
|2021|4|
|2022|9|
|2023|199|
|2024|33121|
|2025|45267|
|2026|96135|

Suman174735, pero no demuestran completitud de ningún año. La población global
NVD no se consultó y se devuelve null, no un porcentaje de cobertura inventado.
Última ingesta verificada: inicio17:41:40 UTC, SUCCESS; as_of KPI17:42:23 UTC.
Esto no se confunde con el watermark incremental de NVD.

### Diseño propuesto

1. **Inventario acotado**, sin writes de producción: ventanas de publicación
   de119 días, resultsPerPage=1 y totalResults para medir faltantes. Ejemplo
   1999–2023: unas77 ventanas; revisar también la fecha inicial real del catálogo.
   Propuesta de tope20MB/20min antes de detener y presentar resultados, no
   una autorización implícita de descarga histórica. Esta fase no se ejecutó.
2. Presentar N faltantes, bytes/riesgos, capacidad libre e impacto de backups.
   Aprobar separadamente un piloto acotado y luego cada campaña de producción.
3. Reutilizar normalización/cargas/checkpoints existentes. Journal separado
   por ventana y página: parámetros, fecha de consulta, totalResults, hash del
   archivo y estado de cada sink. Mantener watermark lastModified diario separado.
4. Páginas durables antes de procesar, lotes pequeños y upserts idempotentes.
   Reanudar la página/sink no confirmado; usar fecha/hash para evitar regresión.
   Ante cambio del conjunto fuente durante paginación, reiniciar esa ventana
   y reconciliar por ID, no asumir un snapshot transaccional del proveedor.
5. Pacing conservador6.2s, backoff/Retry-After y cuota API compartida controlada.
   No activar API key ni crear secretos como efecto secundario del backfill.
6. No avanzar la ventana hasta validación, tres cargas, paridad y KPI verificables.
   Quarantena exige revisión; fallos parciales se recuperan por replay, no por
   borrado automático ni falsa transacción distribuida.
7. Ejecutar fuera de ETL/backup, con estado de pausa preservado, headroom para
   compaction/índices y próxima copia fría. Terminar con DAG activo según el
   procedimiento acordado. Detener por presión de disco/RAM o error de paridad.

### Volumen, duración y costos para decisión posterior

Medición del conjunto actual:814256995 bytes BSON de raw_cve, media4659.95
bytes/CVE, máximo1137517. **No es tamaño HTTP comprimido ni predictor exacto
del histórico**. La cola pesada obliga a medir un piloto.

| Escenario ilustrativo, no descarga autorizada |100000 CVE|1000000 CVE|
|---|---:|---:|
| Raw usando la media BSON actual como proxy |0.466GB|4.66GB|
| Páginas si2000 registros/página |50|500|
| Solo pacing mínimo6.2s/página |5min10s|51min40s|

A eso se suman latencia, reintentos, normalización, cargas y verificación.
**El throughput de escritura histórico no se midió en esta intervención de
lectura; no se da una duración E2E ficticia.** El piloto aprobado debe medir
cada motor y el peor lote antes de presupuestar una campaña.

Para capacidad, una reserva hipotética3–10 veces raw para representaciones,
proyecciones/índices implicaría1.4–4.7GB por100000 CVE, antes de copias y
temporales; **ese multiplicador no está medido ni es garantía**. Cassandra,
Neo4j y backups completos pueden exigir más. No aprobar crecimiento usando
solo esa media o el tamaño de Log4Shell.

La VM/discos actuales ya están provisionados: usar capacidad libre no añade
otra VM, pero sí carga y consumo de espacio. Si hace falta ampliar disco,
el costo es ΔGiB×tarifa regional vigente, previa aprobación. Como referencia
de planificación previa del proyecto, GCS Standard rondaUSD0.02/GB-mes y
pd-balanced USD0.10/GiB-mes; **no son cotización/factura nueva**. Añadir versiones
de backup/soft-delete, transferencia y temporales; Billing sigue fuera de esta
verificación. No se ampliaron recursos ni se descargó histórico en esta tarea.

## Cambios aplicados y compatibilidad

| Archivo | Cambio |
|---|---|
| `services/mcp_server/contracts.py` | Herramientas estrictas, límites de enteros/cadenas, salida tipada, redacción de valores inválidos, serialización equivalente de ambos canales. |
| `services/mcp_server/server.py` | Parámetros explícitos, views/proyecciones, modos de productos, paginación/filtros y snapshot guard. Seis nombres conservados. |
| `services/mcp_server/remote.py` | Registra esas mismas herramientas mediante el constructor. **No cambia el verificador OAuth ni sus ajustes de seguridad**. |
| `services/api/views.py` | Aplicabilidad NVD sin pérdidas, cobertura, metadatos y caché de catálogo de un corte. |
| `services/api/app.py` | Query estricta, proyecciones, productos, metadatos, paginación estable y errores409. |
| `tests/test_api.py`, `tests/test_mcp.py` | Aserciones adaptadas al contrato explícito y parámetros reales. |
| `tests/test_mcp_comprehensive.py` | Nuevas pruebas de schemas, extras, tipos, source pointers, estructura, privacidad, proyección/caché/snapshot. |
| `scripts/verify_mcp_comprehensive.py` | Suite semántica de SDK/HTTP/bases, sin mocks de resultados. |
| `scripts/verify_mcp_comprehensive_native.py` | Misma suite mediante runtime nativo y sus credenciales almacenadas; se detiene si falta login. |
| Probes en `docs/evidence/codex_diagnosis/` | Baseline, staging/canary, integridad, despliegue, volumen y evidencia sanitaria. |

Los datos/canonización histórica y los esquemas de las bases no se cambiaron.
El SDK1.30 descarta extras al construir un modelo de salida TypedDict por
defecto; se corrigió esa ruta para **no perder campos legacy** al añadir
structuredContent. Una prueba específica comprueba las extensiones existentes.
No se modificaron dependencias ni se cambió de SDK para ocultar el defecto.

Activación19:26 UTC: solamente API/MCP, imagen derivada de las existentes,
contexto allowlist sin secretos y canary previo. Código de verificación JWT,
AuthSettings y TransportSecuritySettings **idénticos por comparación AST**.
Los otros11 contenedores, incluida identidad, conservaron IDs. No se tocó
config.toml ni se manipuló el almacén OAuth de Codex.

Hay dos incompatibilidades intencionales/explicadas: extras inválidos dejan de
ignorarse (solicitado) y bool/float no sirven como página. `page="2"` sigue
funcionando. Una página de grafo sin aristas devuelve items=[], total0, no
una arista nula simulada. Los cambios de payload por defecto NO se aplicaron.

## Evidencias, calidad y límites de aceptación

Rutas relativas a `docs/evidence/codex_diagnosis/`:

- `comprehensive_internal_baseline.json`: SDK/HTTP de producción **antes**,
  esquemas completos y los casos concretos de la auditoría.
- `comprehensive_baseline.json`: intento nativo previo bloqueado por sesión.
- `comprehensive_stage.log`, `comprehensive_canary.json`: imágenes y59
  comprobaciones del candidato. Canary no es OAuth E2E.
- `comprehensive_production.json`: **63 PASS y291 invocaciones**, schemas,
  páginas, conteos, estructura y resultados semánticos.
- `comprehensive_database.json`, `comprehensive_database_after.json`: escaneo
  completo de cada motor antes/después,0 duplicados, huellas, catálogo
  independiente y volumen.
- `comprehensive_payload.json`: conteo de ambos canales, sin confundir content
  con tamaño de wire.
- `comprehensive_activation.log`: alcance exacto y tags de rollback.
- `comprehensive_external_auth.json`: discovery200/JWKS200 y rechazos401 sin
  bearer o con bearer inválido. **No equivale a un login OAuth completo**.
- `comprehensive_native_after.json`, `comprehensive_native_suite.json`:
  `notLoggedIn`/PENDING_USER_LOGIN, no schemas nativos frescos ni E2E válido.
- `comprehensive_local_tests.log`:90 PASS/8 SKIP, no se ocultan skips como PASS.
- `comprehensive_final_health.log`: DAG activo,0 runs activos, backup inactivo;
  sin etiquetas de excepción inesperada en el sondeo de API/MCP/Caddy/motores.

Ruff de archivos modificados: PASS; no se afirma lint limpio de archivos
operativos ajenos. Se conservaron fallos del instrumental: path de importación
del contenedor de test y una llave faltante en la medición BSON (antes de
consultas); se corrigieron y repitieron sin cambiar los datos. Las primeras
aserciones unitarias que asumían el contrato viejo también quedaron en logs.
El wrapper de activación terminó con código127 pese a emitir el resultado
APPLIED; no se repitió la operación. Se comprobó el estado aplicado mediante
IDs de contenedores, readiness y la suite posterior sobre producción.

Limitaciones que no se convierten en éxitos:

1. OAuth E2E real y recepción del contrato por Codex App **NOT TESTED** por la
   sesión expirada antes de esta intervención. Pruebas unitarias del verificador
   y metadata pública no suplen esa evidencia.
2. W07 default resumido pendiente de aprobación; legacy aún puede ser grande,
   especialmente al conservar ambos canales. No se promete eficiencia por default.
3. W03 cobertura histórica y W06 discrepancia de fuente permanecen advertidas.
4. Paginación es read-committed, no una instantánea distribuida durante writes.
   Catálogo cacheado requiere reevaluar memoria/latencia antes de un backfill grande.
5. No se conocen todos los argumentos de los96 casos originales: solo los
   explícitos fueron repetidos. No hay declaración de100/100 ni de96/96 PASS.

## Paso requerido del dueño y cierre pendiente

1. En este equipo, Codex App → ajustes MCP → entrada existente
   `big_data_ii_-_threat_intelligence` → **Autenticarse**.
2. Completar personalmente Keycloak/consentimiento. No compartir contraseña,
   URL con code/state ni tokens. No se requiere ningún cambio de Keycloak.
3. Abrir una conversación local nueva para obtener schemas actuales. Avisar
   **«ya autenticado»** para repetir la suite nativa y comprobar los contratos.
4. Opcionalmente ejecutarla tú desde la raíz del proyecto:

   ```powershell
   .\.venv\Scripts\python.exe scripts\verify_mcp_comprehensive_native.py
   ```

   Usa el mismo ejecutable0.167 comprobado; puede indicarse `--binary` si App
   cambió de ubicación. No abre login ni lee/imprime credenciales. Guarda
   `comprehensive_native_suite.json`. GUI E2E sigue pendiente de una llamada
   confirmada desde la interfaz, aunque el runtime nativo llegase a PASS.

La suite está ligada al corte auditado. Si una ingesta legítima cambia as_of,
se detiene con `BASELINE_REFRESH_REQUIRED`: hay que reconciliar nuevas cuentas
y fixtures antes de reusar expectativas, no forzar la producción a números viejos.

Por separado, autorizar o rechazar el cambio incompatible de defaults descrito
en W07. La propuesta de backfill necesita inventario/piloto y aprobación aparte;
no se ejecutará por haber aprobado esta corrección de aplicación.

## Rollback acotado

- Imágenes previas: `ti-app:pre-comprehensive20261111` y
  `ti-mcp:pre-comprehensive20261111`; releases actuales `*:comprehensive20261111`.
- En la VM, `docs/evidence/mcp_comprehensive/previous_sources/` conserva los
  archivos existentes anteriores; `activation.json` registra los dos nuevos.
- Bajo autorización de rollback, verificar que no haya trabajo posterior,
  restaurar solo esas fuentes, retaggear las dos imágenes previas y actualizar
  **solo api y mcp-remote** con --no-deps. No restaurar carpetas completas ni
  borrar archivos nuevos si fueron modificados después por el dueño.
- No restaurar volúmenes ni editar OAuth, credenciales, datos, DAG o otros MCP.
  No se ejecutó rollback porque la integración de aplicación pasó; la falta
  de sesión del dueño ya existía antes y no se resuelve debilitando autenticación.
