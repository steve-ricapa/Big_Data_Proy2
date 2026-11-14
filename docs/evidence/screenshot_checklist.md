# Inventario de capturas para defensa

## Capturas reales disponibles al cierre
- `airflow_success.png`: UI de Airflow con tres ejecuciones exitosas y siete tareas verdes.
- `airflow_dag.png`: grafo de las siete etapas del run scheduler10000.
- `dashboard_overview.png`:171791 CVE y KPI completos.
- `dashboard_explorer.png`: filtros,tabla paginada y detalle de CVE reales.
- `dashboard_analytics.png`: rankings sobre población completa.
- `graph_intelligence.png` y `graph_subgraph.png`: asociaciones reales Neo4j.
- `dashboard_pipeline.png`: última ejecución exitosa y estado real.
- Archivos `*_sample1000.png`:históricos de muestra,no evidencia de volumen completo.

CRUD, esquema/consulta Cassandra, paridad de motores, pruebas y Terraform tienen evidencia JSON/XML/log/CQL auténtica. La tabla siguiente conserva el checklist histórico local; las capturas cloud reales se enumeran al final.

Guardar PNG en `docs/evidence/`; no mostrar secretos. Capturas iniciales de dashboard pueden ser de muestra 1000: el nombre y texto deben indicar ese alcance, no llamarlas carga completa.

| Título | Pantalla/comando | Ruta destino | Qué debe verse / requisito |
|---|---|---|---|
| Inventario | abrir inventory.json | dataset_inventory.png | hashes, 3 feeds, 171791 entradas; volumen |
| Arquitectura | Mermaid system.md | system_architecture.png | tres motores, Airflow, dashboard |
| DAG | http://127.0.0.1:18080, DAG nvd_threat_intelligence, Graph | airflow_dag.png | 7 tareas y dependencias |
| Ejecución | Airflow Grid/run test o log real | airflow_success.png | siete tareas verdes; no confundir test con scheduler |
| Mongo | runner verify y documento API | mongodb_validation.png | conteo y campos raw/canónicos |
| Cassandra | `docker compose exec cassandra cqlsh -e "SELECT * FROM threat_intelligence.cves_by_severity WHERE bucket='CRITICAL' AND month='2024-01' LIMIT 5;"` | cassandra_validation.png | partición real consultable |
| Grafo | Dashboard Graph Intelligence | graph_intelligence.png | CVE, relaciones y productos/CWE reales |
| CRUD | abrir crud.json | crud_engines.png | 12 PASS de tres motores |
| Overview | http://127.0.0.1:18501 | dashboard_overview.png | total, severidad, fecha KPI, promedio separado |
| Rankings | Threat Analytics | dashboard_analytics.png | productos únicos y CWE |
| Explorador | Vulnerability Explorer, filtro CVE | dashboard_explorer.png | paginación y detalle real |
| Pipeline | Data Pipeline | dashboard_pipeline.png | etapas, nuevos/modificados/sin cambios |
| Incremental | incremental.json y log | incremental_validation.png | actualización y no duplicación |
| Terraform | terraform_validate.txt + terraform_plan.txt | terraform_validation.png | 37 altas planeadas, NO aplicadas |
| GCP aplicación | Desplegada: ver sección de capturas cloud | `docs/evidence/screenshots/gcp_*.png` | Solo capturas reales ejecutadas |

Las imágenes presentes son evidencia visual real; las filas sin PNG presente son una checklist pendiente, no capturas fabricadas.
# Capturas posteriores disponibles

| Captura | Ruta exacta | Qué demuestra |
|---|---|---|
| Airflow3 DAG | `docs/evidence/airflow34_dag.png` | Siete tareas y programación del DAG migrado |
| Airflow3 ejecución | `docs/evidence/airflow34_success.png` | Run migration34_20261110T165908,7SUCCESS,Neo4j intento2 |
| Airflow3 full | `docs/evidence/airflow34_full_success.png` | Run full34_20261110T170841,limit0,siete tareas SUCCESS |
| Cassandra/dashboard | `docs/evidence/revalidation_dashboard_cassandra.png` | Threat Analytics muestra fuente Cassandra real y fecha |
| Overview actual | `docs/evidence/revalidation_dashboard_overview.png` | 171791 CVE y KPI reales |
| Explorer actual | `docs/evidence/revalidation_dashboard_explorer.png` | Paginación/detalle con Mongo reader |
| Graph actual | `docs/evidence/revalidation_dashboard_graph.png` | Relaciones Neo4j reales |
| Pipeline actual | `docs/evidence/revalidation_dashboard_pipeline.png` | Estado observado/readiness tres motores; contrastar con JSON de ejecución |

Cloud desplegado el 10-11/11/2026: sección siguiente con capturas reales; antes de esa fecha no existían capturas cloud y no se inventaron.

## Capturas cloud (10-11/11/2026)

Destino `docs/evidence/screenshots/`; generadas con Chrome real por CDP
(`scripts/cloud_dashboard_shots.py`, Basic Auth inyectado sin exponer
contraseña). Dashboard público HTTPS con **174607 CVE por motor** tras
sincronizaciones NVD reales. Filas sin PNG aún = pendientes, no fabricadas.

| Captura | Ruta exacta | Qué debe demostrar |
|---|---|---|
| Cloud Overview | `screenshots/gcp_dashboard_overview.png` | 174607 CVE, KPI con fecha de corte, HTTPS autenticado |
| Cloud Explorer | `screenshots/gcp_dashboard_vulnerability_explorer.png` | Filtros y tabla paginada sobre datos cloud reales |
| Cloud Analytics | `screenshots/gcp_dashboard_threat_analytics.png` | Rankings sobre población completa cloud |
| Cloud Graph histórico | `screenshots/gcp_dashboard_graph_intelligence.png` | Primera captura de tabla; la captura de cierre v2 siguiente sí incluye diagrama SVG |
| Cloud Pipeline | `screenshots/gcp_dashboard_data_pipeline.png` | Estado de sincronización y motores |
| Airflow UI cloud (túnel IAP) | No capturada (opcional) | Corridas acreditadas por JSON/manifiestos, no por captura UI cloud |

Cinco PNG cloud existentes y revisados visualmente. Inventario generado:
`gcp_dashboard_browser_validation.json`. No se mostraron credenciales.

## Capturas cloud de cierre v2 (11/11/2026)

`acceptance_v2/browser.json` inventaría cinco PNG nuevos bajo
`acceptance_v2/screenshots/gcp_dashboard_*.png`: Overview, Explorer, Analytics,
Graph Intelligence y Pipeline. Graph espera el render asíncrono y acredita
`stGraphVizChart` con un SVG, además de las relaciones reales en tabla.
Estas capturas son posteriores a las de la tabla histórica.

## Checklist original y capturas conservadas
