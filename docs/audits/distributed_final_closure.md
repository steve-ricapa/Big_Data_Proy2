# Cierre técnico distribuido — 18/11/2026 UTC

| Componente | Estado observado | Decisión / comprobación |
|---|---|---|
| GCP y Terraform | Tres VMs RUNNING en `us-central1-a/b/c`. Seis discos adjuntos, ningún snapshot Compute listado, sin Cloud Router listado. | El estado Terraform de Cassandra pasó `fmt`, `validate` y `plan` sin deriva. No hubo `apply`. |
| Cassandra | 4.1.9, tres `UN`, 16 tokens por nodo, tres racks, schema agreement; sin streams pendientes, compaction pendiente 0, excepciones 0 en `nodetool info` de los tres nodos. | Mantener `rack1` → `us-central1-a`; comprobar rackdc y gossip, no cambiar etiqueta persistida para igualar nombres. El porcentaje reparado de `nodetool info` no reemplaza la evidencia de la reparación completa anterior. |
| Réplicas / clientes | `dc1:3` NTS para app y auth; API y scheduler `LOCAL_QUORUM`, tres contact points privados. | Conservar reparación y caídas individuales documentadas; no repetir una caída o reparación por auditoría. |
| Ingesta y bases | Run `final_closure_20261118T002607`, 7/7; 1.155 entradas, 43 nuevas, 126 modificadas, 986 sin cambios; sin inválidos ni duplicados. | Paridad nueva de 178.482 por motor y snapshots MongoDB/Cassandra iguales, `as_of` 18/11 00:27:15 UTC. CRUD 12/12 y CRUD de relación tienen evidencia del despliegue distribuido anterior; no se escribieron probes en esta auditoría. |
| API y dashboard | `/ready` y endpoint Cassandra válidos; AppTest 15/15 en cinco vistas con la API real. | No cambiar contratos ni UI. |
| MCP | Seis herramientas en SDK/stdio dentro del contenedor desplegado: respuesta estructurada, igualdad con API y rechazo de argumento desconocido. Discovery OAuth, discovery OIDC y JWKS públicos 200 por HTTPS verificado; MCP sin token 401. | El cliente PKCE existente no llegó a recibir el código (`OAuth flow did not complete within ten steps`). No diagnosticar contraseña ni atribuirlo al funcionamiento de Codex. El dueño confirmó Codex en el cierre anterior; para repetir un E2E público hace falta una sesión interactiva autorizada. No se cambió OAuth ni se publicaron credenciales. |
| Seguridad | JMX limitado a loopback; 7000 y 9042 enlazados a IP privada en cada host; SSH por IAP. La regla heredada web→data usa un tag interno y no publica bases. | CQL e internodo no tienen TLS de aplicación; conservar el perímetro privado. No se amplió la red ni se rotaron credenciales en esta ejecución. |
| Operación | Se detectaron wrappers sin overlay distribuido y rutinas antiguas de instalación/carga incompatibles con el montaje vigente. | Reutilizar `cloud_compose.sh`, incluir overlay en el bundle y bloquear la instalación/carga inicial en una plataforma distribuida. |
| Rendimiento | Observación anterior 6,15 → 14,13 s en un escaneo completo; cambió consistencia y no hubo control de caché/carga. | No optimizar sin benchmark. API abre sesiones por operación; si se justifica, medir p50/p95 bajo carga comparable antes de cambiar ciclo de vida del driver. |
| Pruebas | 96 PASS, 8 SKIP, 0 FAIL; Ruff limpio. | Los 8 SKIP son opt-in de motores privados: 3 probes de salud, 3 CRUD y 2 de permisos (MongoDB/Cassandra). La prueba de permisos Cassandra usa ahora los contact points configurados. No son 8 defectos ni se presentan como PASS de esta suite. |

## Costos y recuperación

Incremento estimado **USD 103,44/mes** (730 h): dos VMs USD 97,84 y 80 GiB de discos USD 5,60. Sumando el escenario base histórico de USD 4,08/día, referencia combinada **≈ USD 227,54/mes**, no factura; tráfico interzona, operaciones y crecimiento GCS pueden cambiarla. Proyecto con facturación habilitada; el importe efectivo requiere acceso al informe de Cloud Billing. En el inventario auditado no hay discos Compute huérfanos. Hay respaldos GCS privados y restauración previa verificada; no se ha ensayado una restauración post-RF=3 ni un reinicio en frío de `ti-dev-data`.

Para una suspensión futura autorizada: verificar respaldo, pausar DAG y temporizadores, dejar acabar escritores y detener ordenadamente servicios antes de parar las VMs. La suspensión completa deja la plataforma fuera de servicio, incluida Cassandra a quorum; al reanudar, verificar montaje, tres `UN`, readiness y sólo entonces reactivar DAG y timers. Discos, GCS, IP pública reservada y otros recursos pueden seguir facturando con VMs apagadas. El retiro permanente requiere inventario y autorización independiente; revisar Terraform de ambos estados y retención de respaldos antes de eliminar recursos. **No se ejecutó ninguna de esas acciones.**

## Fuentes de entrega

- [Arquitectura vigente](../architecture/cassandra-gcp-cluster.md) y [demo sin escrituras](../report/distributed_demo.md).
- [Corte de cierre](../evidence/final_closure/) y [migración, respaldo, CRUD y failover históricos](../evidence/cassandra_cluster/).
- [Matriz académica interna](../implementation/requirements.md): no se encontró un enunciado oficial en los archivos versionados. Separar requisitos documentados de supuestos; no inventar rúbrica ni aportes.
