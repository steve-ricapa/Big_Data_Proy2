# 00 — CONTEXTO MAESTRO · Big Data II – Threat Intelligence

> **Actualización distribuida, 18/11/2026:** para arquitectura, datos y demo vigentes, usar [la adenda](09_distributed_update.md). Las secciones siguientes reconstruyen el **corte histórico del 16/11**, con una VM y RF=1.

> **Documento de transferencia técnica.** Autosuficiente: contiene lo esencial
> para comprender y defender el proyecto. El detalle profundo está en los
> ocho documentos enlazados. Basado en el repositorio `Big_Data_Proy2` (rama
> `main`, commit de cierre `6d947ce`, 16/11/2026) y en la auditoría
> `docs/audits/technical_deliverables_audit.md` (resultado final **10/10 PASS**).

## 1. Qué es el proyecto

Plataforma académica de **Threat Intelligence** sobre el dataset público
**NVD CVE (NIST)**: ingiere vulnerabilidades JSON semiestructuradas, las
normaliza, las carga en **tres motores complementarios** (MongoDB documental,
Cassandra columnar particionado por consulta, Neo4j grafo), calcula KPIs con
reglas explícitas, y expone todo vía API REST, dashboard Streamlit y un
servidor **MCP** para agentes de IA. Todo desplegado en una VM de GCP con
pipeline diario automático.

**Qué NO es**: scanner, detector de ataques, inventario de activos real, ni
sistema HA de producción. Un CVE publicado ≠ ataque confirmado.

**Integrantes**: **DATO PENDIENTE** — no documentados en el repositorio.
El redactor del informe debe obtenerlos del equipo. No inventar ni asignar aportes.

## 2. Los números que hay que saber de memoria (corte 16/11/2026)

| Métrica | Valor | Verificación |
|---|---|---|
| CVE totales (por motor, idénticos) | **176.803** | escaneo completo de pares id+hash |
| Duplicados | **0** (tres motores) | ídem |
| Huella compartida SHA-256 | `6f33b8…bef8d` (64 hex) | Σ sha256(id:hash) mod 2²⁵⁶ |
| Snapshot KPI | **2026-11-16T03:01:29Z** | as_of en Mongo y Cassandra |
| Severidad | CRITICAL 18.080 · HIGH 65.578 · MEDIUM 75.049 · LOW 10.263 · UNKNOWN 7.754 · NONE 79 | agregación independiente ✓ |
| Rejected | 4.036 | ✓ |
| Modificados 30d | 53.876 | ✓ |
| Productos únicos | 23.258 | ✓ |
| CVSS promedio | 3.1: 6,9182 (123.120) · 4.0: 6,2555 (44.441) · 3.0: 7,3050 · 2.0: 6,0833 | ✓ separado por versión |
| Grafo | 634.634 nodos · 1.501.507 relaciones | Neo4j |
| Feeds originales | 1,117 GB · 171.791 entradas (2024-26) | inventario con SHA-256 |
| Pruebas locales | **94 PASS / 8 SKIP / 0 FAIL** · Ruff 0 errores | 16/11 |
| KPIs verificados | **14/14 contrastes independientes PASS** | 16/11 |
| Airflow | 3.4.0 · 7 tareas · success=10/failed=0 | metadata |
| Contenedores | **13/13 healthy** en la VM GCP | docker inspect |
| Auditoría final | **10/10 componentes PASS** | docs/audits |

**Casos de control** (para la demo): Log4Shell `CVE-2021-44228` CVSS 3.1=10.0,
145 productos, 358 CPEs, **559 relaciones** (145 AFFECTS + 358 AFFECTS_CPE +
4 CLASSIFIED_AS + 52 REFERENCES; recuperables sin duplicados en 8 páginas de
73). `CVE-2024-0001`: CVSS 9.8, 4 relaciones.

**Históricos importantes (con fecha, no actuales)**: CRUD 3 motores 12 PASS
(11/11, `acceptance_v2/crud.json`); restore aislado 3 PASS (11/11); suite
cloud 55 PASS (11/11); replay full idempotente 171.791 unchanged × 3 (10/11);
retry real Airflow load_neo4j try_number=2 (10/11); MCP 63 checks SDK→HTTP (11/11).

## 3. Arquitectura en 60 segundos

```mermaid
flowchart LR
  F[Feeds NVD / API incremental] --> A[Airflow 3.4 · DAG 7 tareas diario 03:00 UTC]
  A --> V[ijson + validación + dedup SQLite]
  V --> M[(MongoDB 8 · canónico + raw_cve)]
  V --> C[(Cassandra 4.1 · proyecciones (bucket,mes))]
  V --> G[(Neo4j 5.26 · grafo relaciones)]
  M & G & C --> K[KPIs → snapshots Mongo+Cassandra]
  M & G & C --> API[FastAPI solo lectura]
  API --> D[Streamlit · 5 vistas]
  API --> MCP[MCP · 6 herramientas]
  U[Usuario] --> CD[Caddy TLS 1.3 + Basic Auth] --> D
  AI[Agente IA] --> KC[Keycloak OIDC PKCE] --> MCP
```

GCP: una VM `e2-standard-4` (us-central1-a), discos 30+100 GB, IP reservada,
VPC con firewall (80/443 público; 22 solo IAP; puertos BD solo internos),
2 buckets GCS privados, Secret Manager, Artifact Registry, Monitoring.
13 contenedores Compose. Backup frío diario 02:00 UTC → GCS; restauración
aislada verificada.

## 4. Por qué TRES motores (la pregunta segura del profesor)

| Necesidad | Mongo ✅ | Cassandra ✅ | Neo4j ✅ |
|---|---|---|---|
| Documento original completo flexible | nativo | incómodo | no |
| Consulta (severidad/producto/CWE, mes) pre-particionada | posible pero escanea | **partition key exacta** | anti-patrón |
| Relaciones/grado/vecindad | unwind costoso | no | **traversal nativo** |

Cassandra: tablas `cves_by_{id,severity,product,cwe}` con `PRIMARY KEY
((bucket,month), published DESC, cve_id ASC)` — query-first. Neo4j: 6
constraints únicos; relaciones AFFECTS/AFFECTS_CPE/CLASSIFIED_AS/REFERENCES/
PRODUCED_BY/IDENTIFIES; la aplicabilidad de versiones CPE vive en Mongo raw
(396 ocurrencias vs 358 identidades en Log4Shell) y se une en lectura.
SQLite SOLO es dedup/checkpoint local, no sustituye nada.

## 5. Pipeline en 60 segundos

DAG `nvd_threat_intelligence` (7 tareas seriales): `extract → validate →
load_mongodb → load_cassandra → load_neo4j → calculate_kpis → verify`.
XCom solo rutas. Lotes de 200. Dedup SQLite por lastModified/hash.
Checkpoints por motor SOLO avanzan tras escritura correcta. `verify` escanea
los tres motores y exige huella idéntica; el watermark NVD solo avanza tras
paridad (solape 2h, ventanas ≤119 días, pacing 6.2s, páginas durables
reanudables). Retries=2 con backoff; retry real documentado. Idempotencia
probada: replay completo → written=0 × 3.

## 6. Dashboard y KPIs

Cinco vistas (Streamlit, siempre vía API): **Overview** (4 métricas + 2
gráficos Vega), **Vulnerability Explorer** (filtros combinados CVE/año/
severidad/CWE/fechas + detalle), **Threat Analytics** (3 rankings + lectura
REAL de snapshot Cassandra), **Graph Intelligence** (subgrafo Graphviz
paginado: 559 aristas navegables; página 3 = 59/559), **Data Pipeline**
(manifiesto + readiness 3 motores). Verificado 16/11 por navegador
autenticado HTTPS: 5 vistas sin excepciones (`technical_closure/screenshots/`).

**KPIs top-5 para defender** (fórmulas en doc 05 §5.2-5.3): Total 176.803 ·
Severidad+% (CRITICAL 10,23%) · CVSS por versión separadas · Modificados 30d
53.876 · Productos únicos 23.258. Todos re-verificados 14/14.

## 7. Infraestructura y operación

1. **Aprovisionamiento**: Terraform aplicado 10-11/11 (8 módulos; el
   profesor NO exige reconstruir en vivo).
2. **Despliegue**: bootstrap VM + Compose 13 servicios + roles/secretos.
3. **Operación diaria automática**: backup 02:00 → sync NVD 03:00 → Monitoring.
4. **Actualización**: ejemplo real dashboard 16/11 (imagen separada, 12 IDs intactos, rollback tag).
5. **Recuperación**: restore aislado en scratch verificado (11/11).
Seguridad: IAP-only SSH, TLS 1.3 Caddy, OAuth PKCE MCP, roles read/readWrite,
0 secretos en Git (escaneo verificado).

## 8. Estado de validación (lo defendible y lo honesto)

- **Actual (16/11)**: 94/8/0 pytest, Ruff 0, TF fmt/init/validate PASS,
  paridad+KPIs 14/14, navegador E2E 5 vistas, 13/13 healthy, auditoría 10/10.
- **MCP**: confirmación MANUAL del dueño desde Codex App (16/11); no se
  repitió suite automatizada por instrucción explícita. Presentarlo como
  funcionalidad adicional, no requisito.
- **Limitaciones declaradas** (decirlas antes de que pregunten): sin HA
  (RF=1), sin transacción distribuida (consistencia por verify de huella),
  un escritor a la vez, cobertura NVD parcial (2021:4, 2022:9, 2023:199),
  sin factura GCP real (estimación ~USD 4.08/día histórico), arranque en frío
  no ensayado, restore no reensayado tras 11/11.

## 9. Documentos de este dossier

| Doc | Contenido | Úsalo para |
|---|---|---|
| [01_project_overview](01_project_overview.md) | Problema, dataset, Vs, alcance, requisitos vs adicionales, contradicciones | Cap. 1-2 informe; slides 2-4 |
| [02_architecture_deployment](02_architecture_deployment.md) | Diagramas E2E/secuencia, GCP, contenedores, seguridad, ciclos de vida | Cap. 3+7; slides 3,6,12 |
| [03_databases_models_crud](03_databases_models_crud.md) | Modelos 3 motores, por-qué, CRUD con protecciones, huella de paridad | Cap. 4; slide 5,7; demo CRUD |
| [04_airflow_etl](04_airflow_etl.md) | DAG 7 tareas, sync NVD, idempotencia con evidencias, historial runs | Cap. 5; slides 8-9 |
| [05_dashboard_kpis](05_dashboard_kpis.md) | 5 vistas + catálogo KPIs con fórmulas/valores/fecha + top-5 | Cap. 6; slides 10-11 |
| [06_validation_evidence](06_validation_evidence.md) | Resultados actuales vs históricos, matriz evidencias→uso, prioridad capturas | Cap. 8; anexos |
| [07_report_ppt_blueprint](07_report_ppt_blueprint.md) | Índice informe capítulo a capítulo, 14 slides con tiempos, guion demo 8-10 min con planes B | ESQUELETO de entrega |
| [08_file_inventory](08_file_inventory.md) | Todas las rutas con función y relevancia ★ | Referencia de trazabilidad |

## 10. Reglas para el redactor

1. Toda cifra lleva fecha de snapshot; nunca mezclar histórico con actual.
2. Todo PASS cite su evidencia (ruta del doc 06 §6.6 o del 08).
3. Integrantes/roles: PENDIENTE — preguntar al equipo.
4. MCP = valor agregado con confirmación manual; no prometer suite nueva.
5. No ejecutar CRUD/restore/backfill en la exposición sin autorización.
6. Limitaciones del §8: presentarlas como decisiones conscientes documentadas.
7. La rúbrica original del profesor NO está en el repo; la matriz de 17
   criterios (`docs/implementation/requirements.md`) es del equipo. Requisito
   histórico confirmado: ≥50.000 registros y los tres motores.
