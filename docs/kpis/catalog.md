# Catálogo de KPI

Todos se recalculan tras cargas exitosas, por ejecución diaria o manual; persistencia `MongoDB.kpis/latest`, `Cassandra.kpi_snapshots/latest` y artefacto `kpis.json`. La API/dashboard muestra fecha `as_of`. Fuente base: documentos canónicos Mongo; población incluye Rejected (se informa su número), sin asumir explotación. Conteo de producto/fabricante/CWE es por CVE distinto, no por ocurrencia de CPE.

| KPI / objetivo | Fórmula y fuente | Limpieza / interpretación / limitación |
|---|---|---|
| Total CVE / volumen | N de documentos únicos por cve_id | Dedup antes de cargar; no número de ataques. Cobertura solo feeds locales |
| Distribución severidad / priorización | n(severidad)/N ×100, más conteo | CVSS preferido 4.0 >3.1 >3.0 >2.0; Primary primero, source ordenada. UNKNOWN incluido en denominador. Distribución combina categorías de distintas versiones, no scores comparables |
| Publicaciones mensuales / tendencia | count(CVE con published UTC en mes) | Sin inferir tendencia real de ataques; cambios de cobertura NVD sesgan serie |
| Top CWE / tipos de debilidad | número de CVE que incluyen cada CWE; top20 | Solo `CWE-\d+`, se excluye noinfo/Other. Un CVE puede contar en varios CWE: sumas no deben igualar N |
| Top productos / exposición asociada | count distinct CVE por [part,vendor,product]; top20 | Solo CPE vulnerable y componentes identificables; no inventar productos faltantes. Varias versiones no multiplican producto |
| Top fabricantes / asociaciones | count distinct CVE por vendor; top20 | Vendor literal CPE; varios productos del mismo fabricante cuentan una vez por CVE |
| CVSS promedio / score por versión | sum(score_v)/count(score_v), separado para 2.0/3.0/3.1/4.0 | Solo métricas seleccionadas válidas finitas 0–10; UNKNOWN excluido, no cero. El promedio v3.1 no incluye los CVE con v4 preferido; no media global mezclada |
| Modificados 30 días / actividad de revisión | count(as_of−30d ≤ last_modified ≤ as_of) | Ventana UTC inclusiva, excluye futuro. Actualizar no significa nuevo ataque. Datos posteriores al corte no incluidos |
| Tamaño grafo / estructura | count(nodos), count(relaciones), fuente Neo4j | Incluye entidades huérfanas históricas; no equivale a CVE ni entidades actualmente afectadas |
| Productos únicos / cobertura | cardinalidad de identidades de producto | No cantidad de cadenas CPE. Datos ausentes no implican producto seguro |

Pruebas: `tests/test_core.py` cubre ventana temporal, porcentaje, métricas ausentes, medias separadas, dedup de producto y extracción vulnerable. Verificación completa de identidad/hash entre motores es adicional; no reemplaza la revisión semántica de cada KPI. La suma de severidades y meses debe igualar total; rankings pueden superponerse.
