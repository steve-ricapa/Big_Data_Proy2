# 01 — Contexto, problema y alcance del proyecto

## 1.1 Identidad del sistema

| Campo | Valor verificado |
|---|---|
| Nombre | Threat Intelligence Platform · Big Data II |
| Propósito | Plataforma académica de análisis de vulnerabilidades NIST NVD (CVE) con tres motores de datos complementarios, pipeline ETL orquestado, API, dashboard y servidor MCP para agentes de IA |
| Entrega académica | 16/11/2026 (fecha registrada en `README.md:3`) |
| Repositorio | `https://github.com/steve-ricapa/Big_Data_Proy2` (rama `main`, cierre en commit `6d947ce`) |
| Proyecto GCP | `proyectobigdata2-514216` |
| Endpoint público | `https://ti-136-114-21-18.sslip.io` (HTTPS, Basic Auth para web; OAuth OIDC para MCP) |
| Integrantes | **DATO PENDIENTE**: no documentados en el repositorio; el redactor debe obtenerlos del equipo. No inventar nombres ni aportes. |

## 1.2 Problema real que resuelve

El National Vulnerability Database (NVD) publica diariamente miles de
vulnerabilidades (CVE) como documentos JSON semiestructurados. El problema
tiene tres dimensiones que una sola base de datos no resuelve bien:

1. **Conservar el documento original completo** (configuraciones CPE con
   árboles booleanos AND/OR, todas las métricas CVSS, referencias) para
   auditoría y reprocesamiento → requiere un almacén documental.
2. **Responder consultas analíticas de producción** ("¿qué CVE CRITICAL
   afectaron el producto X en enero de 2024?") con baja latencia sobre
   176803 registros → requiere particionamiento por clave de consulta.
3. **Representar y explotar relaciones** (CVE→producto, CVE→CWE,
   CVE→referencia, producto→fabricante, CPE→producto) y responder preguntas
   de grado/conectividad → requiere un grafo.

La plataforma integra los tres modelos y añade: actualización incremental
diaria sin duplicación, KPIs con reglas explícitas, API REST de solo lectura,
dashboard analítico y un servidor MCP (Model Context Protocol) que permite a
agentes de IA como Codex consultar los datos de forma segura.

**Qué NO es** (limitación explícita del proyecto, `README.md:38`):
- No es un scanner ni detector de ataques.
- No es un inventario real de activos empresariales.
- Un CVE publicado no equivale a un ataque confirmado.

## 1.3 Justificación del enfoque Big Data

**Volumen**: 171791 entradas en los feeds originales (1.117 GB de JSON);
176803 CVE tras sincronizaciones incrementales con la API NVD. Escaneo
completo de tres motores con huella SHA-256 en cada verificación.

**Variedad**: JSON semiestructurado con anidamiento profundo y variable
(configuraciones booleanas recursivas, métricas CVSS en 4 versiones,
descripciones multilingües, CPE 2.3 con escapes). Se normaliza a un
documento canónico con hash de contenido.

**Velocidad**: sincronización diaria automática 03:00 UTC vía API NVD 2.0
(lastModStartDate/lastModEndDate) con watermark que solo avanza tras
verificar paridad en los tres motores. Última ventana: 132 registros en
~2 minutos (03:00–03:02 UTC).

**Veracidad/valor**: registros Rejected (4036) se conservan y se informan,
no se eliminan; scores CVSS no se mezclan entre versiones; UNKNOWN no se
imputa a cero. Cada KPI declara su fórmula y limitación en `docs/kpis/catalog.md`.

**Procesamiento**: streaming con `ijson` (nunca cargar el GB completo en
memoria), deduplicación en SQLite temporal en disco del contenedor (evita
I/O aleatorio sobre bind mount Windows), lotes de 200 con checkpoints por motor.

## 1.4 Fuente de datos y dataset

**NVD CVE API 2.0 / feeds anuales** (`https://services.nvd.nist.gov/rest/json/cves/2.0`).

Feeds originales inmutables en `data/raw/nvd/<año>/`:

| Feed | Bytes | Entradas |
|---|---:|---:|
| nvdcve-2.0-2024.json | 293.745.058 | 39.369 |
| nvdcve-2.0-2025.json | 295.852.585 | 45.482 |
| nvdcve-2.0-2026.json | 527.484.894 | 86.940 |
| **Total** | **1.117.082.537** | **171.791** |

Inventario con hashes: `docs/evidence/inventory.json`, generado por
`src/threat_intelligence/ingestion/nvd.py:12-37` (streaming ijson + SHA-256).

Cobertura observada por año de **publicación** (no del ID):
2021:4, 2022:9, 2023:199, 2024:33121, 2025:45267, 2026:96135 al corte del
11/11 (`docs/evidence/codex_diagnosis/comprehensive_payload.json`).
**La cobertura histórica es parcial**: la carga inicial fueron los feeds
2024–2026 más sincronizaciones de ventana; CVE antiguos no modificados
recientemente (p.ej. CVE-2021-45046) pueden faltar. Esto se declara en
metadata de la API (`coverage.is_complete_nvd_history: false`).

## 1.5 Casos de uso de Threat Intelligence cubiertos

1. **Búsqueda y filtrado**: por CVE exacto, severidad, CWE, año/rango de
   publicación, texto libre (índice text de MongoDB).
2. **Análisis de severidad**: distribución y evolución temporal (mensual).
3. **Priorización**: ranking de productos/fabricantes/CWE por CVE distintos.
4. **Análisis de grafo**: relaciones salientes de un CVE (productos, CPEs,
   CWEs, referencias) con paginación completa hasta 559 aristas.
5. **Vigilancia continua**: sincronización diaria + KPI "modificados en 30 días".
6. **Consulta por agentes de IA**: seis herramientas MCP de solo lectura con
   OAuth OIDC (funcionalidad adicional, no requisito académico original).

## 1.6 Alcance y limitaciones REALES (defender ante el profesor)

| Aspecto | Estado real | Evidencia |
|---|---|---|
| HA / tolerancia a fallos de nodo | NO. Un nodo por motor, Cassandra RF=1 | `docs/data_models/cassandra.md:3` |
| Transacción distribuida entre motores | NO. Consistencia eventual por verify de huella post-carga | `docs/architecture/system.md:75-77` |
| Escritores concurrentes | NO soportados. Un pipeline a la vez (CLI o Airflow) | `README.md:61` |
| TLS productivo local | NO en local; SÍ en cloud (Caddy TLS 1.3) | README sección GCP |
| Descarga NVD local | SÍ vía `runner sync`; programada en cloud | `src/threat_intelligence/ingestion/sync.py` |
| Backfill histórico completo | NO ejecutado; diseño aprobado pendiente | `docs/integrations/mcp_comprehensive_remediation.md` |
| Centralidad/PageRank en grafo | NO. Solo degree counts | `docs/data_models/neo4j.md:27` |
| Certificación de seguridad | NO. Es un proyecto académico | README |

## 1.7 Requisitos académicos vs funcionalidades adicionales

La rúbrica original del profesor **no está en el repositorio** (verificado
16/11; `docs/audits/technical_deliverables_audit.md` §1). La matriz de 17
criterios en `docs/implementation/requirements.md` fue elaborada por el
equipo. Requisito histórico registrado: **≥50.000 registros y los tres
motores obligatorios** (`docs/implementation/initial_readme.md:4,24-25`) —
cumplido con 176803.

**Requisitos académicos nucleares** (de la matriz del equipo, trazables):

| # | Requisito | Estado al cierre |
|---|---|---|
| 1 | Dataset ≥50k procesado | 176803 CVE verificados |
| 2 | MongoDB real | PASS (auditoría 16/11) |
| 3 | Cassandra real | PASS |
| 4 | Neo4j real | PASS |
| 5 | DAG ≥6 etapas | 7 tareas, PASS |
| 6 | Actualización incremental | Diaria automática, PASS |
| 7 | CRUD tres motores | 12 PASS históricos (11/11) + código |
| 8 | ≥5 KPIs correctos | 14 contrastes PASS (16/11) |
| 9 | Dashboard real | 5 vistas, PASS navegador 16/11 |
| 10 | Pruebas automatizadas | 94 PASS / 8 SKIP (16/11) |
| 11 | Docker | 13 contenedores healthy |
| 12 | Terraform validado | fmt/init/validate PASS |
| 13 | Costos con supuestos | USD ~4.08/día estimado (histórico) |

**Funcionalidades adicionales** (valor agregado, no exigidas originalmente):
- Servidor MCP remoto con OAuth OIDC/Keycloak PKCE S256 (6 herramientas).
- Respaldo frío coordinado diario + restauración aislada verificada.
- Observabilidad: 5 políticas Monitoring + sondas periódicas.
- API FastAPI con contratos estrictos y vistas summary/legacy.
- Auditoría técnica completa con huellas criptográficas entre motores.

## 1.8 Contradicciones y datos no verificables (honestidad académica)

1. `README.md` pre-cierre mezclaba conteos históricos (174607/174734) con
   instrucciones vigentes; corregido el 16/11 (commit `6d947ce`).
2. Suites históricas 47/55 PASS (11/11) NO son los 94 PASS actuales; no sumar.
3. El retry real de Airflow (`load_neo4j try_number=2`) es del 10/11, histórico.
4. Restauración de backup: evidencia del 11/11 (174607 registros); no reensayada.
5. Facturación GCP real: no accesible (IAM Billing 403); solo estimación con SKU.
6. Integrantes y reparto de trabajo: no documentados en el repo.
