# Entrega local — Threat Intelligence Platform

> **Resumen histórico conservado.** Para el estado vigente tras migración a
> Airflow3.4,42tests,MCP local y usuarios Mongo mínimos, consultar
> [`revalidation_delivery.md`](revalidation_delivery.md) y
> `docs/evidence/revalidation_state.json`. **Para el despliegue GCP real
> verificado E2E (10-11/11/2026), el documento vigente es
> [`final_delivery.md`](final_delivery.md).** Las afirmaciones2.11/MCP ausente de
> este documento describen el primer cierre, no el runtime recomendado actual.

**10 de noviembre de 2026. Plataforma local funcional y verificada. GCP desplegado y verificado E2E desde el 10-11/11/2026 (ver final_delivery.md).**

**Bloqueo productivo:** auditoría Airflow2.11 reportó421 hallazgos en59 paquetes. No se corrigieron ni se ocultan:su migración y nueva verificación son pendientes técnicos. Scheduler/webserver propios quedan detenidos,con inicio opt-in solo para demo local aislada. Ver `docs/implementation/security_review.md`. El porcentaje siguiente mide los17 criterios funcionales/documentales,no certificación de seguridad.

## A. Estado general
17/17 criterios locales de finalización implementados y verificados: **100% / 100%**, según [trazabilidad](../implementation/requirements.md). Este porcentaje no incluye extras opcionales MCP/despliegue cloud ni afirma seguridad productiva. Informe y guion preparados/revisados, sin afirmar ensayo oral cronometrado.

## B. Componentes funcionales
ETL streaming, MongoDB8, Cassandra4.1, Neo4j5.26, checkpoints por motor, CRUD, KPI, API FastAPI, dashboard Streamlit de cinco vistas y Airflow2.11 con siete tareas. Carga completa por CLI con funciones compartidas; Airflow ejecutado con1000 y10000 entradas. Scheduler recuperó conexión Neo4j deliberadamente rechazada en el segundo intento. DAG quedó pausado para evitar cargas inesperadas.

## C. Pruebas
**37 pytest aprobadas,0 fallidas,0 omitidas en Docker:**31 de código/contrato y6 de motores reales. Windows repite31 y omite6 por aislamiento:no sumar suites duplicadas. Adicionalmente:CRUD12 operaciones,incremental5 escenarios,HTTP12 comprobaciones,KPI9 comprobaciones independientes yDAG7 tareas exitosas. Evidencias XML/JSON/logs en `docs/evidence/`.

## D. Datos

| Motor | CVE únicos verificados |
|---|---:|
| MongoDB |171791|
| Cassandra |171791|
| Neo4j |171791|

171791 entradas válidas,0 inválidas,0 duplicadas. Los tres motores comparten huella de todos los pares identidad/hash. Grafo:617044 nodos y1467881 relaciones. KPI:17707 críticos,21784 productos únicos;CVSS promedio separado por versión. No equivalen a ataques confirmados.

## E. Infraestructura
Compose real ejecutado,imágenes app/Airflow construidas,dependencias app bloqueadas con hashes,motores sin puertos publicados,web solo loopback. Terraform fmt/init/validate/plan correctos:**37 altas planeadas,0 cambios,0 bajas;ninguna aplicada**. No se habilitaron APIs,subieron datos ni crearon recursos cloud por el agente.

## F. Costos
Escenario académico de una std4:aprox **USD4.04/día oUSD122.84/mes amortizados**,con discos/reserva auxiliar,bajo supuestos de us-central1. No costo facturado ni autorización de consumo. Fuente/supuestos/otros escenarios en [estimación](../architecture/gcp_cost_estimate.md). Reconfirmar SKU/región,tipo de cambio e impuestos antes de aprobar.

## G. Evidencias y documentación
- `docs/evidence/delivery_state.json`, `full_run.json`, `full_kpis.json`:resumen/artefactos completos exportados.
- `full_optimized.log` y `full_recovery.log`:fallo de conteo Cassandra y recuperación sin reescrituras,seguida de carga/paridad total.
- `integration_tests.xml`, `crud.json`, `incremental.json`, `kpi_audit.json`, `http_validation.json`.
- `scheduler_retry.json`, `airflow_retry_attempt=1.log`, `airflow_retry_attempt=2.log`.
- PNG reales:Overview,Explorer,Analytics,Graph,Pipeline yAirflow. Checklist distingue capturas presentes de pendientes opcionales.
- [Informe de20 secciones](technical_report.md), [guion24 minutos](demo_script.md), [progreso](../implementation/progress.md), modelos y catálogo KPI.

## H. Pendientes externos y limitaciones
Despliegue GCP requiere aprobación explícita. Migración de seguridad Airflow pendiente técnico sin requisito de permiso cloud. Antes de producción:TLS,auth Cassandra,mínimo privilegio,backup/restore/capacidad. No hay MCP ni descargador automático NVD;incremental recibe feeds locales. CI preparado,no ejecutado remotamente;sin Git/commits/pushes. Sin HA/transacción distribuida;un pipeline a la vez.

## I. Acceso y comandos de demostración
Dashboard **http://127.0.0.1:18501**, API **http://127.0.0.1:18000/docs**, Airflow **http://127.0.0.1:18080**. Login Airflow admin;contraseña local privada en secrets/airflow-admin-password,no capturar ni publicar.

```powershell
docker compose run --rm --no-deps runner verify --run-dir data/staging/full_optimized
docker compose run --rm --no-deps runner crud --output docs/evidence/crud_demo.json
docker compose run --rm --no-deps runner selftest --output docs/evidence/incremental_demo.json
docker compose run --rm --no-deps tester -q -p no:cacheprovider
```

Ejecutar secuencialmente,sin DAG activo paralelo. Apagado sin borrar datos ni otros proyectos:`powershell -File scripts/stop-local.ps1`. Instalación/inicio completo y costos en README.
