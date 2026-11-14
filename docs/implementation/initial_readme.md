# Threat Intelligence Big Data — README histórico anterior a implementación

Proyecto universitario de análisis de vulnerabilidades NIST NVD (CVE 2024,
2025 y 2026), con al menos 50,000 registros y futuras actualizaciones
incrementales. Entrega: **16 de noviembre de 2026**.

## Estado y alcance

Este repositorio contiene la estructura inicial y una preparación de
infraestructura **sin desplegar**. No implementa procesamiento, DAGs, consultas,
APIs, servidor MCP ni dashboard. No se han instalado dependencias ni creado
recursos cloud. Terraform modular prepara el escenario económico; Compose
define contenedores locales, sin haberlos iniciado.

Plan GCP, costos, permisos, bloqueos TLS y comandos de revisión:
[`docs/architecture/gcp-deployment-plan.md`](docs/architecture/gcp-deployment-plan.md),
[`gcp-costs.md`](docs/architecture/gcp-costs.md) y
[`gcp-operations.md`](docs/architecture/gcp-operations.md).
Configuración local: [`infrastructure/docker/README.md`](infrastructure/docker/README.md).

El objetivo de despliegue es **Google Cloud**, con un presupuesto de **S/ 1,000
en créditos**. La selección de servicios, región, versiones y dimensionamiento
queda pendiente. Se priorizarán opciones administradas solo cuando sean
compatibles con el presupuesto y con los motores obligatorios originales:
**MongoDB, Apache Cassandra y Neo4j**; no se sustituirán por equivalentes GCP.
El valor de presupuesto en `.env.example` es informativo: no crea alertas ni
limita gastos automáticamente.

## Componentes previstos

- **Apache Airflow:** orquestar tareas; importar procesamiento desde `src/`,
  sin duplicar lógica de negocio en los DAGs.
- **Paquete Python:** ingestión, validación, transformación, acceso a bases,
  análisis e incrementales compartidos por los consumidores.
- **MongoDB, Cassandra y Neo4j:** persistencia con modelos y responsabilidades
  por definir mediante los casos de consulta.
- **Streamlit:** dashboard analítico.
- **API y MCP:** futuras interfaces de consulta para aplicaciones y agentes.
  La conexión desde ChatGPT requerirá definir transporte, autenticación,
  compatibilidad y acceso seguro; no está disponible en esta etapa.

## Organización

| Directorio | Responsabilidad |
| --- | --- |
| `data/raw/nvd/{2024,2025,2026}/` | JSON originales inmutables, excluidos de Git. |
| `data/staging/` | Datos intermedios de validación y preparación. |
| `data/processed/` | Salidas listas para consumo o carga. |
| `data/samples/` | Futuras muestras pequeñas y revisadas; datos excluidos de Git por defecto. |
| `infrastructure/terraform/` | Futuros módulos y entorno `environments/dev/`. |
| `infrastructure/docker/` | Futuras definiciones de imágenes. |
| `infrastructure/scripts/` | Automatización exclusiva de infraestructura. |
| `airflow/` | DAGs, plugins, configuración y pruebas de orquestación. |
| `src/threat_intelligence/ingestion/` | Lectura de fuentes. |
| `src/threat_intelligence/validation/` | Calidad y contratos de datos. |
| `src/threat_intelligence/transformations/` | Normalización y transformaciones. |
| `src/threat_intelligence/databases/` | Adaptadores de MongoDB, Cassandra y Neo4j. |
| `src/threat_intelligence/graph/` | Construcción y procesamiento de relaciones. |
| `src/threat_intelligence/analytics/` | Cálculo de indicadores. |
| `src/threat_intelligence/incremental/` | Futura detección de cambios y checkpoints. |
| `src/threat_intelligence/common/` | Utilidades compartidas estrictamente necesarias. |
| `services/` | Puntos de entrada independientes: `api/`, `mcp_server/`, `dashboard/`. |
| `database/` | Esquemas, índices y scripts nativos por motor; no adaptadores Python. |
| `tests/` | Pruebas unitarias, de integración y de extremo a extremo. |
| `notebooks/` | Exploración reproducible; no lógica de producción duplicada. |
| `docs/` | Arquitectura, dataset, modelos, KPIs, evidencias e informe. |
| `scripts/` | Futuras utilidades operativas del proyecto. |
| `.github/workflows/` | Automatización CI futura, aún sin workflows. |

Los directorios vacíos se conservan mediante `.gitkeep`. El paquete utiliza
layout `src/`, Python >=3.11 y metadatos PEP 621 en `pyproject.toml`.
Las dependencias de ejecución siguen vacías: su selección y compatibilidad
con Airflow se resolverán antes de instalar herramientas.

## Dataset inspeccionado

Los tres archivos son documentos JSON UTF-8 con objeto raíz, metadatos
`format: NVD_CVE`, `version: 2.0` y un arreglo `vulnerabilities`.
Se verificó la sintaxis completa, no la calidad semántica ni la unicidad de CVE.

| Archivo bajo `data/raw/nvd/` | Bytes | Entradas |
| --- | ---: | ---: |
| `2024/nvdcve-2.0-2024.json` | 293745058 | 39369 |
| `2025/nvdcve-2.0-2025.json` | 295852585 | 45482 |
| `2026/nvdcve-2.0-2026.json` | 527484894 | 86940 |
| **Total** | **1117082537** | **171791** |

El inventario y los hashes están en `docs/dataset/inventory.md`. El año de
ubicación corresponde al nombre del feed, sin afirmar que todas sus fechas
internas pertenezcan a ese año. No modificar ni reformatear los originales.
Los datos, incluidos staging y salidas, están excluidos de Git y del contexto
Docker. No usar `git add -f` para incorporarlos.

## Uso inicial y siguientes pasos

1. Revisar el inventario y los requisitos de entrega antes de procesar datos.
2. Copiar `.env.example` a `.env` y completar solo las variables necesarias
   cuando se definan los servicios. El archivo no se carga automáticamente.
   No guardar credenciales en código; para GCP preferir ADC o identidad de carga.
3. Definir casos de consulta, KPIs, contratos, deduplicación por CVE y política
   de actualización basada en cambios; decidir checkpoints e idempotencia.
4. Diseñar modelos e índices nativos de los tres motores y pruebas de calidad.
5. Estimar costos y elegir topología, región, versiones y recursos GCP antes
   de escribir infraestructura; contemplar almacenamiento, cómputo y apagado.
6. Acordar dependencias, versiones y entornos de ejecución; después implementar
   módulos compartidos, pruebas y DAGs delgados.
7. Implementar servicios y controles de acceso, validar incrementales y
   reunir evidencias para la entrega.

No ejecutar despliegues sin autorización explícita. Las guías describen
operaciones futuras; Cloud Run sigue desactivado y TLS GCP requiere preparación.
