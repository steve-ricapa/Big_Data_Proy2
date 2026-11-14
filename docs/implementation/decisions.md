# Decisiones técnicas

1. Conservar infraestructura existente y los JSON originales. No re-descargar datos válidos.
2. Python 3.11 aislado, Airflow 2.11.0: interoperabilidad de drivers y contenedores. No instalar Airflow nativo en Windows.
3. Streaming `ijson`, NDJSON canónico por ejecución y hashes de contenido. XCom solo transporta rutas/manifiestos, nunca el dataset.
4. MongoDB guarda el documento canónico y el original CVE. Cassandra modela consultas con particiones mensuales; Neo4j usa identidades CPE y relaciones extraídas, no inferidas.
5. Estado incremental independiente por motor. Un fallo Cassandra/Neo4j no queda oculto porque MongoDB haya avanzado. Actualizar checkpoints solo tras escritura correcta.
6. CVSS preferido 4.0 > 3.1 > 3.0 > 2.0, conservando versión. Promedios separados por versión, nunca una media global mezclada.
7. Costos cloud no autorizados: trabajo local y Terraform validate/plan únicamente. No APIs nuevas ni recursos cloud.
8. SQLite temporal en disco contenedor y checkpoints en volumen `checkpoint_data` tras medir latencia sobre bind Windows. NDJSON/manifiestos visibles en host; migración sin sobrescribir destino.
9. Red edge para web loopback18000/18501/18080; motores solo interna. No reutilizar puertos de otros proyectos.
10. Verificación reforzada: huella de todos los pares CVE/hash más conteos; no declarar cada arista validada por esta huella.
11. Lock app con hashes; Airflow constraints oficiales independientes para evitar conflictos de versiones.
12. Full:Cassandra escribió todos los registros pero COUNT(*) final falló por timeout del coordinador. Sustituido por escaneo paginado de cve_id, no aumento ciego de timeout cliente. Reintentar con checkpoints conservados;no recargar171791 documentos ya confirmados.
13. Revalidación posterior: recuperar endpoints Docker recreando solo contenedores propios,
    sin borrar volúmenes ni detener otros proyectos. No asumir que healthy implica DNS.
14. Conteo Mongo sin filtros usa índice de identidad; fechas API son fechas de calendario,
    no solo regex. Snapshot Cassandra se consulta directamente desde API/dashboard.
15. MCP opcional aislado por stdio y acceso al proceso local, sin herramientas destructivas,
    credenciales de bases ni listener HTTP. No equivale a integración ChatGPT remota.
16. Migración Airflow 3.4 en metadata/volúmenes separados: conservar historial 2.11.
    No aprobar el cambio por versión/auditoría solamente: exigir ejecución del DAG y retry.
17. Mongo runtime separado: `ti_pipeline` readWrite solo en la base del proyecto;
    `ti_reader` read para API. La credencial administrativa solo se monta en
    `mongo-init`. Usuarios se crean sin resetear contraseñas existentes.
18. Exclusión `docs/evidence/` del contexto Docker: las evidencias se montan al
    ejecutar, no se necesitan ni deben inflar imágenes/transferencias de build.
19. Medición real del Explorer: año/rango publicados tardaban ~5.5s frente a
    ~0.1s de severidad/CWE. Añadir índices de publicación/año con ID para evitar
    escanear documentos completos. Conservar mediciones antes y después;
    no inferir año publicado a partir del feed ni del identificador CVE.
20. Puente ADC para Terraform: token impersonado efímero solo en el entorno del
    hijo, sin claves JSON ni ADC alterado; el primer apply directo falló
    `invalid_grant` y el puente lo resolvió sin cambiar credenciales.
21. IP externa reservada estable + hostname sslip.io: mantiene OAuth/DNS
    estables sin dominio propio ni balanceador; Caddy como único punto HTTPS
    (80/443), sin CloudRun por costo/complejidad.
22. OIDC con Keycloak real (realm `ti`, cliente confidencial PKCE S256) en vez
    de OAuth artesanal; administración/master no públicos (404 vía `route` de
    Caddy, orden de handlers explícito).
23. Sincronización NVD como artefactos durables por páginas en el run_dir,
    watermark del estado global avanzando solo tras verify de paridad; el
    solape de 2h re-procesa idempotentemente (unchanged), no duplica.
24. MongoDB cloud con `mem_limit` 2g tras OOM en 157200 registros; reanudar
    desde checkpoints sin re-descargar feeds válidos ni tocar costo.
25. Respaldo frío coordinado desde la VM con subida privada a GCS usando la
    identidad de la VM (metadata token), nunca credenciales en texto plano;
    pausa el DAG y solo reanuda si estaba ACTIVO; restauración verificada en
    volumen aislado contra la huella del último verify exitoso.
26. Imágenes durables en Artifact Registry con writer acotado al repositorio
    para la SA de la VM; token de docker en DOCKER_CONFIG temporal eliminado
    tras el push, catálogo del registro como verificación independiente.
27. Cadencia diaria explícita: respaldo 02:00 UTC → sincronización NVD 03:00
    UTC con el DAG ACTIVO al cierre; telemetría cada 5 min y alerta de edad de
    sincronización para detectar bloqueos silenciosos.
28. Cierre v2: los cuatro healthchecks faltantes se declaran en Compose, pero
    no se recrean servicios para activarlos. Sondas externas cada60s y su edad
    alimentan la métrica unhealthy_containers existente. La telemetría solo
    considera las13 instancias canónicas, no clientes scratch con labels heredados.
29. CRUD cloud condicionado a identidad ausente, con limpieza en finally;
    Cassandra IF NOT EXISTS y TTL. No inicializar esquemas desde el probe ni
    reutilizar CVE reales. Regresión final cloud55 PASS, Windows47 PASS/8 SKIP.
30. Restore real de tres motores desde nuevas descargas GCS privadas, sin
    volúmenes productivos montados. JVM requiere hostname resoluble aun con
    red none: --hostname ti-restore y entrada127.0.0.1, solo en scratch.
    Primeros fallos preservados; reintento y posterior descarga GCS dieron3 PASS.
31. Vincular huella esperada al último verify ANTERIOR al respaldo, no a la
    base actual: backup02:00 tiene174607 CVE y sync03:00 avanzó a174734.
    Todos los contenedores scratch quedan detenidos; sus volúmenes privados
    y las descargas se conservan en el disco existente para inspección.
32. Reconstrucción controlada con cuatro etiquetas nuevas de verificación,
    sin reemplazar imágenes productivas. Añadir .dockerignore al bundle y
    exigir su presencia antes del build. No se afirma reproducibilidad byte
    a byte ni recreación desde host vacío/VM nueva; bases por tag, no digest.
