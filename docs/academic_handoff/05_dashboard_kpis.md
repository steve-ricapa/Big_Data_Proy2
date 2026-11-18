# 05 — Dashboard y KPIs

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](09_distributed_update.md).

## 5.1 Las cinco vistas

Archivo: `services/dashboard/app.py` (Streamlit; datos SIEMPRE vía API HTTP,
nunca directo a bases). Capturas actuales (16/11, Chrome autenticado HTTPS):
`docs/evidence/technical_closure/screenshots/*.png`.

### Vista 1 — Overview
- **Objetivo**: estado global de la plataforma en 4 métricas + 2 gráficos.
- **Fuente**: `GET /api/v1/kpis` (snapshot Mongo).
- **Visualizaciones**: 4 `st.metric` (CVE únicos, Críticos, Modificados 30d,
  Productos identificables) + `st.bar_chart` severidad + `st.line_chart`
  mensual (Vega-Lite SVG) + JSON de CVSS por versión y tamaño del grafo.
- **Implementación**: `app.py:46-77`. Captura: `screenshots/overview.png`.

### Vista 2 — Vulnerability Explorer
- **Objetivo**: búsqueda filtrada y paginada + detalle.
- **Fuente**: `GET /api/v1/vulnerabilities` y `/{cve_id}`.
- **Filtros**: CVE exacto, año publicación, severidad, CWE, rango fechas, página.
- **Validación UI**: CVE/CWE/fechas inválidos → warning visible (422 API).
- **Implementación**: `app.py:78-114`. Captura: `screenshots/vulnerability_explorer.png`.

### Vista 3 — Threat Analytics
- **Objetivo**: rankings y CONSULTA REAL A CASSANDRA (no solo Mongo).
- **Fuente**: `/api/v1/kpis` + `/api/v1/analytics/cassandra/snapshot`
  (endpoint que abre sesión Cassandra y lee `kpi_snapshots`).
- **Control de consistencia**: si as_of Cassandra ≠ Mongo muestra warning.
- **Tablas**: top CWE / fabricantes / productos (20 c/u).
- **Implementación**: `app.py:63-73,243-257` (API). Captura: `screenshots/threat_analytics.png`.

### Vista 4 — Graph Intelligence
- **Objetivo**: explorar relaciones salientes de un CVE.
- **Fuente**: `GET /api/v1/graph/cve/{id}` (paginado, filtro por tipo).
- **Controles** (añadidos 16/11): CVE, página, tamaño (25/73/100/250),
  tipo de relación (AFFECTS/AFFECTS_CPE/CLASSIFIED_AS/REFERENCES/Todas).
- **Visual**: dataframe + `st.graphviz_chart` (SVG DOT); caption indica
  página, totales filtrados/totales y continuación.
- **Verificado en navegador**: página 3 de Log4Shell = 59 de 559, "Fin de resultados".
- **Implementación**: `app.py:115-134` (API `app.py:288-323`). Captura: `screenshots/graph_intelligence.png`.

### Vista 5 — Data Pipeline
- **Objetivo**: estado del ETL y readiness de los tres motores.
- **Fuente**: `/api/v1/pipeline/status` (manifiesto más reciente; status
  SUCCESS/FAILED/IN_PROGRESS_OR_INTERRUPTED) + `/ready` (ping Mongo+Cassandra+Neo4j).
- **Implementación**: `app.py:135-140`. Captura: `screenshots/data_pipeline.png`.

## 5.2 Catálogo completo de KPIs

Fuente de cálculo: `src/threat_intelligence/analytics/kpis.py:5-52`.
Persistencia: Mongo `kpis.latest` + Cassandra `kpi_snapshots` + `data/staging/<run>/kpis.json`.
Definiciones y limitaciones: `docs/kpis/catalog.md`.
Verificación independiente 16/11: 14/14 contrastes PASS (`docs/evidence/technical_closure/runtime.json`).

**Snapshot de referencia: 2026-11-16T03:01:29.397074+00:00** (tras el DAG de las 03:00 UTC).

### K-01 Total de CVE
- **Fórmula**: `total = |{documentos únicos por cve_id}|`
- **Motor**: MongoDB (conteo completo). Implementación: iteración + contador.
- **Valor**: **176.803** (16/11). Incluye 4.036 Rejected (se informan por separado).
- **Interpretación**: volumen cargado; NO número de ataques; cobertura parcial del histórico NVD.

### K-02 Distribución por severidad (conteo y %)
- **Fórmula**: `n(sev) = count(severity = sev)`; `pct(sev) = round(n(sev)·100/total, 4)`
- **Motor**: Mongo (agregación `$group` independiente para verificar).
- **Valores**: CRITICAL 18.080 (10,2261%) · HIGH 65.578 (37,0910%) · MEDIUM
  75.049 (42,4478%) · LOW 10.263 (5,8048%) · UNKNOWN 7.754 (4,3857%) · NONE 79 (0,0447%).
- **Regla**: severidad derivada del CVSS preferido (4.0>3.1>3.0>2.0, Primary
  primero); UNKNOWN en denominador, sin imputar a cero; categorías de
  versiones distintas no son scores comparables.

### K-03 Publicaciones por mes
- **Fórmula**: `count(published ∈ [mes])` sobre mes UTC de publicación.
- **Motor**: Mongo (`$group` por `month`; verificado igual al snapshot).
- **Valor**: diccionario completo en snapshot (gráfico de líneas Overview).
- **Interpretación**: tendencia de publicación; sesgada por cobertura de feeds/sync.

### K-04 Promedio CVSS por versión
- **Fórmula**: por v ∈ {2.0,3.0,3.1,4.0}: `avg(v) = Σ score_v / count(v)` (redondeo 4 dec.)
- **Motor**: Mongo (agregación `$match cvss≠null`, `$avg` por versión).
- **Valores**: 3.1: 123.120 @ **6,9182** · 4.0: 44.441 @ **6,2555** · 3.0:
  1.452 @ **7,3050** · 2.0: 36 @ **6,0833**.
- **Interpretación**: medias SEPARADAS — nunca mezclar versiones; la media
  v3.1 excluye CVEs que tienen v4 preferida.

### K-05 Modificados en los últimos 30 días
- **Fórmula**: `count(as_of − 30d ≤ last_modified ≤ as_of)` (ventana UTC inclusiva).
- **Motor**: Mongo (count_documents con rango ISO — verificado).
- **Valor**: **53.876** al corte 16/11 03:01 UTC.
- **Interpretación**: actividad de REVISIÓN de NVD, no nuevos ataques.

### K-06 Productos únicos afectados
- **Fórmula**: `|{identity = [part,vendor,product]}|` sobre CPE vulnerable.
- **Motor**: Mongo (`$unwind products` + `$group` — verificado 23.258).
- **Valor**: **23.258**. Versiones CPE NO multiplican; no cantidad de cadenas CPE.

### K-07 Top CWE (ranking 20)
- **Fórmula**: `count(CVE con CWE=w)`; solo `CWE-\d+`; un CVE cuenta en varios CWE.
- **Verificado**: cada entrada del top contrastada con `count_documents({cwes: id})`.

### K-08 Top productos / K-09 Top fabricantes (ranking 20)
- **Fórmula**: CVE distintos por identidad de producto / por vendor literal CPE.
- **Verificado**: ídem entrada por entrada. Vendor = literal CPE, sin verificación corporativa.

### K-10 Rejected CVEs
- **Fórmula**: `count(status == "Rejected")`. **Valor**: **4.036**. Permanecen en población.

### K-11 Tamaño del grafo
- **Fórmula**: `count(nodos)`, `count(relaciones)` — Motor: Neo4j.
- **Valor**: **634.634 nodos / 1.501.507 relaciones**. Incluye entidades históricas huérfanas.

## 5.3 Los 5 KPIs recomendados para defender

| KPI | Por qué defenderlo con este |
|---|---|
| **K-01 Total (176.803)** | Volumen Big Data; supera 3.5× el mínimo de 50k; paridad 3 motores con huella SHA-256 |
| **K-02 Severidad + % (18.080 CRITICAL / 10,23%)** | Priorización; muestra reglas de CVSS por versión y honestidad del UNKNOWN |
| **K-04 CVSS por versión (3.1:6,92 vs 4.0:6,26)** | Decisión técnica sofisticada: medias separadas, no mezclar escalas |
| **K-05 Modificados 30d (53.876)** | Demuestra la sincronización diaria viva y el costo real de mantener datos frescos |
| **K-06 Productos únicos (23.258)** | Conecta con Neo4j/Cassandra: identidad por [part,vendor,product], versiones no multiplican |

Justificación de exclusión: rankings (K-07..09) son fáciles de explicar pero
menos "defendibles" analíticamente; K-11 depende de huérfanos históricos.

## 5.4 Auditoría independiente de KPIs

`src/threat_intelligence/analytics/audit.py` re-calcula cada KPI con
agregaciones de base (no releyendo el snapshot) y contrasta entrada por
entrada los rankings; verifica además snapshot Cassandra == Mongo y conteos
del grafo. Comando: `runner audit-kpis --output docs/evidence/kpi_audit.json`.
Resultado 16/11: **14/14 checks PASS** (ver `runtime.json`).
