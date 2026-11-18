# 07 — Blueprint: informe técnico, PPT y demostración

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](09_distributed_update.md).

> NO es el informe final ni el PPT. Es la estructura para que otro asistente los redacte.
> **Integrantes: DATO PENDIENTE** — obtener del equipo; no inventar nombres ni reparto.

## A. Índice del informe técnico

### Portada y preliminares
- Título sugerido: "Plataforma de Threat Intelligence sobre NVD con MongoDB, Cassandra y Neo4j".
- Autores (PENDIENTE), curso, fecha, repositorio, URL pública.

### 1. Introducción (1.5–2 págs)
- 1.1 Problema y motivación (usar `01_project_overview.md` §1.2).
- 1.2 Objetivos (general + específicos medibles: ≥50k registros, 3 motores, DAG ≥6 etapas, ≥5 KPIs, CRUD, dashboard).
- 1.3 Alcance y limitaciones (§1.6 — honestidad como fortaleza).
- **Tabla**: requisitos académicos vs adicionales (§1.7).
- **Traza**: cada objetivo → capítulo → evidencia (ruta).

### 2. Datos y justificación Big Data (2 págs)
- 2.1 Fuente NVD y dataset (tabla de feeds, hashes, cobertura por año — §1.4).
- 2.2 Las V del proyecto (§1.3).
- 2.3 Casos de uso (§1.5).

### 3. Arquitectura (3–4 págs)
- 3.1 Visión extremo a extremo → **insertar diagrama Mermaid §2.1 (renderizado)**.
- 3.2 Flujo de datos → **diagrama de secuencia §2.2**.
- 3.3 Justificación de tres motores → **tabla comparativa `03_...md` §3.0** (clave del trabajo).
- 3.4 Seguridad (roles, OAuth, TLS, IAP — `02_...md` §2.8).
- 3.5 Decisiones técnicas relevantes → extraer 8–10 de `docs/implementation/decisions.md` (SQLite dedup, índices por medición, IP reservada+sslip, Airflow3 separado...).

### 4. Modelos de datos (4–5 págs)
- 4.1 Mongo: documento canónico + raw, índices (con la historia de los 5.5s→0.1s).
- 4.2 Cassandra: tablas, partition/clustering keys y POR QUÉ (query-first); ejemplo CQL.
- 4.3 Neo4j: grafo, constraints; aclarar aplicabilidad CPE vive en raw.
- **Insertar**: esquema JSON anonimizado (03 §3.1), tablas CQL (03 §3.2), grafo Mermaid.
- 4.4 CRUD: tabla por motor + mecanismo de protección + evidencia crud.json.

### 5. Pipeline y orquestación (3–4 págs)
- 5.1 DAG 7 tareas → **diagrama §4.2** + explicación por tarea.
- 5.2 Incremento/dedup/idempotencia → **tabla con evidencias** (`04_...md` §4.4).
- 5.3 Sync NVD (ventanas, watermark tras paridad).
- 5.4 Reintentos + retry real. 5.5 Historial (tabla de 10 runs).

### 6. Dashboard y KPIs (3 págs)
- 6.1 Cinco vistas (tabla: objetivo/fuente/visual + captura pequeña c/u).
- 6.2 Catálogo KPI con fórmulas (copiar §5.2 de `05_...md`).
- 6.3 Los 5 KPIs defendidos con valores y snapshot date (§5.3).

### 7. Despliegue e infraestructura (2–3 págs)
- Tabla de recursos (§2.4), 13 contenedores, persistencia/backup/monitoreo.
- Ciclos de vida 1–5 (§2.7): aclarar "no se reconstruye en vivo".
- Costos estimados con supuestos.

### 8. Validación y resultados (2–3 págs)
- Paridad/huella; 94/8/0; 14/14 KPI; navegador E2E; Terraform; matriz de evidencias (§6.6).
- Histórico vs actual claramente separado.

### 9. Trabajo futuro (1 pág)
Backfill NVD (diseño existe), HA, MVCC/snapshot distribuido, defaults MCP summary, ensayo de arranque en frío.

### Anexos
A: matriz evidencias→capítulos. B: auditoría 10/10 referencia. C: MCP como valor agregado. D: glosario (CVE, CPE, CVSS, CWE, KPI, ETL...).

---

## B. Estructura del PPT (14 diapositivas ~20 min)

| # | Título | Mensaje central | Visual | Evidencia base | Min |
|---|---|---|---|---|---|
| 1 | Portada | Título, equipo (PENDIENTE), curso | Logo/ur l pública | — | 0.5 |
| 2 | Problema | NVD publica masivo semiestructurado; una BD no basta | 3 íconos de necesidad | `01 §1.2` | 1.5 |
| 3 | Solución y alcance | Plataforma 3 motores + ETL + API + dashboard (+MCP opcional) | Diagrama simplified E2E | `02 §2.1` | 1.5 |
| 4 | Dataset y Vs | 1.1GB/171.791→176.803; Volumen/Variedad/Velocidad/Veracidad | Tabla feeds + 4 chips V | `01 §1.3-1.4` | 1.5 |
| 5 | ¿Por qué 3 motores? | Cada necesidad → su motor óptimo | **Tabla comparativa §3.0** | `03` | 2.5 |
| 6 | Arquitectura | Extremo a extremo real | Diagrama Mermaid render | `02 §2.1` | 2 |
| 7 | Modelos de datos | Mongo canónico+raw / CQL partition-first / grafo | 3 mini-esquemas | `03` | 2 |
| 8 | Pipeline ETL | 7 tareas, incremental, idempotente | Diagrama DAG §4.2 | `04` | 2 |
| 9 | Idempotencia demostrada | Replay full: 171.791 unchanged × 3 | Números grandes | `airflow34_full_manifest` | 1 |
| 10 | Dashboard | 5 vistas funcionando | Captura overview + graph | `screenshots/` | 1.5 |
| 11 | KPIs top-5 | Valores reales con fecha de snapshot | Tarjetas KPI | `05 §5.3` | 2 |
| 12 | Infraestructura GCP | VM+13 contenedores+backup+monitoring | Captura console + tabla | `06 §6.2` | 1.5 |
| 13 | Validación | 10/10 auditoría; paridad huella; 94 PASS | Tabla resumen | `audits` | 1 |
| 14 | Conclusiones + futuro | Objetivos cumplidos; siguientes pasos | Checklist | — | 1 |

**Regla**: máximo 1 visual por slide; cifras SIEMPRE con fecha de snapshot.

---

## C. Demostración (duración total sugerida: 8–10 min)

### Secuencia óptima (de menor a mayor riesgo, con plan B por paso)

| Paso | Qué mostrar | Dónde | Dur | Riesgo | Plan B |
|---|---|---|---|---|---|
| 1 | Dashboard Overview: 176.803 y 4 métricas | `https://ti-136-114-21-18.sslip.io` (Basic Auth) | 1.5' | bajo | captura `overview.png` |
| 2 | Explorer: filtrar CVE-2024-0001 → 1 resultado; luego filtro contradictorio → 0 | ídem | 1' | bajo | `vulnerability_explorer.png` |
| 3 | Threat Analytics: caption "Snapshot Cassandra" (demostrar motor 2) | ídem | 1' | bajo | captura |
| 4 | Graph: CVE-2021-44228, ir a página 3 → 59/559 "Fin de resultados" | ídem | 1.5' | bajo | `graph_intelligence.png` |
| 5 | Airflow UI (túnel IAP 18081): grid del DAG, últimos runs success | `http://127.0.0.1:18081` | 1.5' | medio (túnel) | `gcp_airflow_ui_grid.png` + tabla runs de runtime.json |
| 6 | (SI AUTORIZADO) CRUD: `runner crud` en cloud con guardas | `scripts/cloud_closure_v2.py crud` | 2' | **escribe** | mostrar `crud.json` + explicar protecciones TTL/IF NOT EXISTS |
| 7 | KPIs: API `/api/v1/kpis` con as_of visible | curl/docs | 1' | bajo | snapshot runtime.json |

### Pre-demo checklist
- [ ] VM RUNNING y 13/13 healthy (`docker ps` por IAP).
- [ ] Credencial web Basic Auth disponible SIN proyectarla.
- [ ] Túnel IAP a 18081 abierto antes de empezar.
- [ ] Sin DAG en ejecución (backup 02:00/sync 03:00 ya pasaron; horario de clase seguro).
- [ ] Capturas de respaldo abiertas en pestañas.
- [ ] NO ejecutar CRUD sin autorización explícita del docente en ese momento.

### Riesgos y mitigaciones
1. **Caída de red/VM**: todas las capturas del 16/11 están en el repo.
2. **Túnel IAP falla**: usar captura del grid + metadata JSON.
3. **Pregunta "¿esto es producción?"**: responder límites honestos (§1.6) — es académico, un nodo, sin HA.
4. **Pregunta "¿por qué no solo Mongo?"**: tabla §3.0 — 3 necesidades distintas.
5. **Pregunta por exactitud de datos**: huella SHA-256 idéntica en 3 motores + 14 checks KPI independientes.
