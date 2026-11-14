# Revisión de seguridad — bloqueo de uso productivo

**La plataforma está verificada funcionalmente en local, pero NO está aprobada para producción.**

## Actualización posterior: runtime recomendado migrado

Airflow **3.4.0 slim**, lock con hashes y 145 paquetes instalados:
**0 hallazgos Python conocidos**, `airflow34_dependency_audit.json`.
Aplicación con MCP opcional: 63 paquetes, **0 hallazgos conocidos**,
`mcp_dependency_audit.json`. Scheduler real con 10000 entradas, siete SUCCESS
y reintento Neo4j verificado. Metadata 2.11 preservada separadamente y detenida.
Detalles y comandos: `airflow3-migration.md`.

Mongo ahora separa usuario ETL readWrite y API read-only; bootstrap administrativo
opt-in. Un test real verifica lectura y rechazo de escritura con código 13.
MCP stdio no tiene acceso a credenciales de bases ni listener público.

**La auditoría y los pendientes 2.11 descritos abajo son históricos**, no el
runtime recomendado vigente. Conservarlos da trazabilidad, no autoriza reutilizar
esa imagen en producción. Persisten límites de OS/JVM, TLS, Cassandra auth,
Neo4j Community, backups/restore y controles de producción. Cero avisos conocidos
no equivale a cero vulnerabilidades ni a permiso de desplegar.

## Auditoría ejecutada

| Alcance | Resultado real | Evidencia |
|---|---|---|
| Dependencias de aplicación, lock con hashes | Sin vulnerabilidades conocidas reportadas | `docs/evidence/dependency_audit.json` |
| Paquetes instalados en imagen Airflow 2.11.0 | **421 hallazgos en 59 paquetes** | `docs/evidence/airflow_dependency_audit.json` y `.log` |

El segundo conteo es el reportado por pip-audit; no significa 421 ataques ni necesariamente 421 CVE únicos, pues pueden existir alias/avisos relacionados. Incluye Airflow y proveedores/dependencias que la aplicación no usa. No se auditó exhaustivamente el sistema operativo/JVM de todas las imágenes. No afirmar que el conjunto está libre de vulnerabilidades.

## Controles locales aplicados
- Sin puertos de MongoDB, Cassandra, Neo4j o PostgreSQL publicados.
- API/dashboard/Airflow enlazados solo a loopback; red de datos interna separada de presentación.
- Secretos locales aleatorios, fuera de imágenes, ignorados; no se leyeron ADC ni imprimieron tokens/contraseñas.
- Auth temporal del navegador borrada tras las capturas.
- DAG pausado al terminar; **scheduler y webserver de este proyecto detenidos por seguridad tras la validación**. Otros proyectos Docker no se tocaron.
- Servicios Airflow en perfil opt-in `orchestration`; el script de inicio exige `-WithAirflow` para iniciarlos. La demo local debe ser temporal, aislada y con usuario administrador de confianza.
- Sin operaciones cloud facturables ni despliegue del stack vulnerable.

Estos controles reducen exposición, **no corrigen las vulnerabilidades**. Una interfaz loopback tampoco elimina todos los riesgos del navegador local.

## Pendientes originales (estado actualizado)
1. Migración/dependencias mínimas: completada y verificada localmente con 3.4.
2. Reconstrucción, auditoría, importación y ejecución con retry: completadas;
   resultados en `airflow34_*`. No se afirma auditoría completa de OS/JVM.
3. Antes de cloud: TLS, autenticación/autorización Cassandra, usuarios mínimos Mongo, backups/restauración y revisión de red/identidad.

El despliegue GCP sigue requiriendo aprobación explícita. Las evidencias 2.11
se conservan como históricas; las nuevas ejecuciones 3.4 tienen nombres propios.
