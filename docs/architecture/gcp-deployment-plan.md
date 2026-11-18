# Plan de despliegue GCP — Threat Intelligence

> **Referencia histórica anterior a la expansión de Cassandra.** Las cifras, pruebas y comandos son de su corte original, no instrucciones vigentes para GCP. Para la arquitectura y operación actuales, consultar [el cierre distribuido](../audits/distributed_final_closure.md).

> **Plan operativo vigente y prueba de conexión:**
> [gcp_deployment_readiness.md](gcp_deployment_readiness.md).
> Este documento conserva la propuesta inicial; el apartado de funcionalidades
> futuras está superado por la implementación local verificada. Airflow vigente
> es3.4.0 con paralelismo1; inicialmente se recomienda una VM con acceso IAP,
> sin Cloud Run. APIs faltantes yegress deben resolverse con autorización.

Estado: **preparación, sin despliegue**. Fecha de revisión: 10/11/2026.
Entrega académica: 16/11/2026. Presupuesto: S/1,000. Datos: 171,791 entradas.

## Decisión

Seleccionar **A, una VM e2-standard-4 (4 vCPU, 16 GiB)** en us-central1-a,
Debian 12, disco de arranque 30 GiB y disco de datos 100 GiB pd-balanced.
MongoDB Community, Cassandra Apache y Neo4j Community conservan sus motores
originales. PostgreSQL solo almacena metadatos Airflow. LocalExecutor con
paralelismo 2 evita Redis/Celery y gastos adicionales. No GKE, Composer, NAT,
balanceador, Atlas, Astra ni Aura. No se compra ningún compromiso de consumo.

```text
Operador -- IAP SSH + OS Login --> VM privada de datos
NVD --> GCS raw --> Airflow --> módulos src --> tres motores --> GCS processed
Clientes -- HTTPS + IAM --> Cloud Run (API, MCP, Streamlit; futuros)
                                  | Direct VPC egress, TLS verificado
                                  v
                         VM IP privada, puertos limitados
Secret Manager --> identidades específicas; Artifact Registry --> imágenes
Cloud Run logs / métricas nativas GCE --> Logging / Monitoring
```

No alta disponibilidad: fallo de VM o zona detiene todas las bases y Airflow.
100 GiB es una provisión inicial, no una medición del tamaño final: índices,
commitlogs, compaction de Cassandra y backups exigen espacio adicional.
Implementar streaming y cargas por lotes; no leer los tres JSON simultáneamente
en memoria. Validar consumo real antes de ampliar a e2-standard-8.

## Estado real de implementación

- Ocho módulos Terraform locales, proveedor google fijado a 6.49.0, sin módulos
  remotos. Código local se versionará junto al repositorio; no existe todavía
  commit Git. Conservar `.terraform.lock.hcl` después de un init autorizado.
- VPC propia, /24 (espacio para Direct VPC), Private Google Access, SSH solo IAP.
- Sin SSH global, reglas públicas de bases ni bindings `allUsers`.
- IAM por identidad, GCS por bucket, secretos por recurso, sin claves de SA.
- Secret Manager crea solo nombres, nunca versiones ni valores en state.
- Discos cifrados en reposo por Google; TLS hacia bases **pendiente**.
- API/MCP/dashboard omitidos (`web_services = {}`), no imágenes de ejemplo.
  Se exige digest para activarlos, 0–1 instancia por servicio y autenticación IAM.
  Direct VPC sin conector facturable; salida privada únicamente hacia bases.
- Alertas CPU y métrica de errores Run; sin canales no hay notificación externa.
  Logging Run es nativo. No se ha instalado Ops Agent: logs Docker y memoria/disco
  huésped no se exportan todavía. Rotación local limita el crecimiento.
- No políticas de gasto automáticas ni backend remoto bootstrapado por Terraform.

## Salida a Internet: decisión explícita

Default `allow_external_egress_ip=false`. Private Google Access no proporciona
acceso a apt, Docker Hub o NVD. El bootstrap requiere filesystem preparado y
salida; no fingimos que puede completar en ese estado.

Opción recomendada para demo, **pendiente de aprobación**: IP externa efímera
solo para salida en la VM. Firewall sigue denegando todos los ingresos salvo
IAP. Presupuestar USD 0.005/h mientras esté encendida. No IP estática reservada.
Alternativa sin IP: imagen de VM preconstruida y contenedores en Artifact
Registry mediante Private Google Access; preparar ese flujo antes de desplegar.
No crear Cloud NAT sin justificación y autorización adicionales.

## Seguridad y separación local/GCP

Compose raíz es exclusivamente local, red interna, bases sin `ports` y Airflow
en loopback. Cassandra local conserva configuración de desarrollo, por lo que
**no autoriza su uso en GCP**. Ver `infrastructure/docker/README.md` para las
pruebas TLS, autenticación, usuarios de aplicación y montajes que bloquean la
exposición privada de bases. El firewall no sustituye cifrado ni autenticación.

No iniciar workloads automáticamente en startup-script; tampoco clonar código,
copiar secretos a metadata ni subir datos. Bootstrap se detiene ante disco vacío
para que un operador confirme explícitamente su inicialización. Docker Engine
se instala del repositorio oficial en una ejecución futura; los paquetes host
no están fijados por versión (pendiente imagen dorada). Las imágenes de
contenedores sí tienen tags fijados; resolver digest y revisar CVEs antes de uso.

Cloud Run exige `roles/run.invoker` e ID token con audiencia del servicio.
Para navegador usar proxy autenticado o diseñar autenticación de usuario, no
abrir dashboard a todo Internet. MCP IAM no garantiza compatibilidad directa
con ChatGPT: queda pendiente transporte HTTP, OAuth/adaptador compatible,
autorización y revisión de exposición. Un `MCP_AUTH_TOKEN` aislado no sustituye
este diseño. Probar límites de conexión y duración de sesiones/Streamlit.

## Requisitos funcionales futuros (no implementados aquí)

DAG programado propuesto: extraer incremental → validar → normalizar/deduplicar
→ cargar MongoDB → cargar Cassandra → cargar Neo4j → KPIs/checkpoint.
Checkpoints solo después de éxito; upserts idempotentes; XCom solo referencias
GCS. Importar funciones de `src`, no copiar procesamiento al DAG.

CRUD en los tres motores, integración dashboard con los tres y cinco KPIs
pendientes. Candidatos: CVE por año, distribución de severidad CVSS, porcentaje
crítico/alto, principales CWE y latencia publicación–modificación (definiciones
y denominadores aún por validar). Infraestructura preparada no acredita esos
requisitos ni 171,791 CVE únicos.

## Alternativas

| Escenario | Diseño | Decisión |
| --- | --- | --- |
| A | Una VM + Run | Seleccionado para 6 días de desarrollo/demo, menor operación. |
| B | Cassandra std4, Mongo/Neo std4, Airflow std2 | Menor contención, más RAM y costo; módulos reutilizables pero root dev solo ensambla A. |
| C | 3 Cassandra std4, 3 Mongo std4, 1 Neo std4, 1 Airflow std2 | Solo referencia. Replica set/RF=3 multizona requieren configuración adicional. Neo Community y Airflow siguen sin HA. |

No se ofrecen Atlas/Astra/Aura: no son necesarios y añadirían tiers,
restricciones/red y costos de proveedores; no se afirma una cotización de ellos.
Neo4j Community no proporciona cluster HA de Enterprise. C no debe describirse
como plataforma completamente HA. Usar múltiples VMs no crea replicación sola.

Costos: [gcp-costs.md](gcp-costs.md). Operación y permisos:
[gcp-operations.md](gcp-operations.md).
