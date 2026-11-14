# Auditoría inicial — 10 noviembre 2026

Inspección real de todos los archivos no-dataset: solo hay infraestructura inicial, README, inventario y el `__init__.py` del paquete. No hay repositorio `.git`, DAGs, lógica de procesamiento, tests, dashboard ni API. No se declara un motor funcionando por existir Compose.

| Requisito | Estado inicial | Acción |
|---|---|---|
| >=50k registros | Inventario previo 171791 entradas, pendiente recuento streaming | Verificar archivos y hashes |
| MongoDB/Cassandra/Neo4j | Imágenes declaradas, daemon inicialmente detenido | Arrancar localmente y probar motores reales |
| ETL/incremental | No implementado | Procesamiento streaming, manifiestos por ejecución y estado por motor |
| DAG >=6 tareas | No existe | DAG diario idempotente |
| CRUD | No existe | Pruebas aisladas en motores reales |
| KPI/dashboard | No existe | Agregación sobre documentos canónicos y dashboard de datos reales |
| Terraform | Módulos existentes, CLI fuera de PATH | Conservar, instalar CLI temporal y validar |
| Documentación/evidencias | Solo preparación inicial | Registrar resultados ejecutados, no supuestos |

## Riesgos
- Python predeterminado 3.14: usar 3.11 aislado por compatibilidad con Airflow 2.11 y Cassandra.
- RAM 16 GB, memoria libre inicial ~1.2 GB; Docker tiene límite ~8 GB. Ejecutar servicios escalonadamente y medir antes de una carga completa.
- Compose no construye imágenes de aplicación; secretos requeridos aún no existen; Airflow no monta datos ni instala drivers.
- Cassandra sin autenticación solo es aceptable dentro de la red local privada; no desplegar esta configuración públicamente.
- Credenciales GCP no se inspeccionan ni se imprimen. Solo consultas, validación/plan; apply/destroy y operaciones cloud facturables requieren autorización.

Esta auditoría describe el punto de partida, no el estado final. Ver `progress.md` y evidencias.

## Nueva inspección 10/11/2026, 16:30 UTC en adelante

El repositorio contiene ya ETL, adaptadores, siete tareas Airflow, API, cinco
vistas Streamlit, tests y evidencias de carga completa. Se ha leído código de
los componentes y repetido pruebas reales; no se asume funcionamiento solo por
los archivos. Sin `.git`; no se inicializa ni publica por inferencia.
Hay secretos locales existentes: se respetan, no se muestran ni se regeneran.

Incidencias nuevas y verificación: `revalidation.md`. Matriz actual completa:
`requirements.md`. Pendiente local prioritario: seguridad Airflow 2.11 y nueva
verificación de migración sin sobrescribir metadata válida. MCP aún ausente
al iniciar esta revisión. Python host 3.14, venv 3.11 existente; Docker 8 GiB,
otros proyectos activos no se detienen. Los directorios `.gitkeep` vacíos son
organizativos, no funcionalidad faltante cuando existe código equivalente.
