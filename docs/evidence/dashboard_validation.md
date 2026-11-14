# Validación dashboard/API

## Revisión posterior vigente
API usa Mongo read-only. Readiness comprueba MongoDB,Cassandra yNeo4j.
`scripts/verify_http.py`:14 comprobaciones reales PASS. Threat Analytics lee
snapshot directamente de Cassandra y muestra fecha;captura real
`revalidation_dashboard_cassandra.png`. Fechas de calendario/rango validadas.
Airflow3.4 UI autenticada y run real de siete tareas exitosas,Neo4j intento2:
`airflow34_success.png`. Las referencias2.11/12HTTP siguientes son históricas.

Cinco vistas de nuevo navegadas en navegador real con Mongo reader:
`revalidation_dashboard_overview.png` (171791 visibles),
`revalidation_dashboard_explorer.png` (171791 resultados),
`revalidation_dashboard_cassandra.png`, `revalidation_dashboard_graph.png`
(subgrafo real), `revalidation_dashboard_pipeline.png` (readiness tres motores).
La captura Pipeline refleja el estado observado durante ensayo full; el JSON
de ejecución y no una captura aislada determina si el ensayo terminó.

## Cierre con carga completa
Cinco vistas navegadas con agent-browser:dashboard_overview.png,dashboard_explorer.png,dashboard_analytics.png,graph_intelligence.png/graph_subgraph.png,dashboard_pipeline.png. Overview171791 CVE,17707 críticos,21784 productos únicos. HTTP12 nuevamente PASS tras carga completa,detalles en http_validation.json. Airflow autenticado localmente,UI y Graph7 tareas verdes:airflow_success.png/airflow_dag.png. Perfil temporal de auth eliminado sin mostrar contraseña.

## Historial inicial
Los PNG sample1000 y las cifras siguientes son históricos;las restantes vistas ya se verificaron con el volumen completo como indica el apartado anterior.

API `http://127.0.0.1:18000`, Streamlit `http://127.0.0.1:18501`, healthchecks saludables. `scripts/verify_http.py`:12 comprobaciones reales PASS (liveness,readiness Mongo/Neo4j,KPI,listado,rankings,estado,detalle,grafo,422,404,health Streamlit). Respuestas en http_validation.json; readiness explicita motores comprobados, no incluye Cassandra.

Browser agent-browser abrió Overview real:1000 CVE,244 críticos,24 modificados30d,742 productos; promedio3.1=7.3428 (983 métricas),4.0=6.6 (5). Snapshot `2026-11-10T08:09:26.945008+00:00`, no extrapolar a completo. Captura `dashboard_overview_sample1000.png`; Explorer `dashboard_explorer.png`. Restantes vistas pendientes de comprobación visual final.

Primera prueba8000 retornó404 del servicio no esperado; Docker no publicó web solo en red interna. Red edge y puertos18000/18501/18080 corrigieron acceso sin tocar aplicaciones ajenas ni publicar motores. Script HTTP pasó tras corrección.

Error API/motor se muestra, no datos simulados. Caché30s/actualización manual y fecha de snapshot. Manifiesto distingue FAILED/SUCCESS/IN_PROGRESS_OR_INTERRUPTED; última categoría no garantiza proceso vivo.
