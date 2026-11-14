# Contenedores

Las bases usan directamente imágenes oficiales fijadas por tag en Compose.
No se crean Dockerfiles que solo repitan `FROM` sin aportar configuración.
Antes de desplegar verificar tags, parches, licencias y registrar digests
inmutables en Artifact Registry (la versión del tag no fija bytes).

`docker-compose.yml` es **solo desarrollo local aislado**: ninguna base tiene
puertos publicados. Red data interna; red edge publica solo web en loopback.
Cassandra es un único nodo, RF=1 para futuros keyspaces; no es HA.
Su imagen por defecto no exige autenticación: nunca publicar este Compose
en una red GCP. Los healthchecks comprueban disponibilidad, no CRUD ni TLS.

Archivos locales en `secrets/` (ignorados, generados por `scripts/prepare_local.py` sin imprimir valores):

- `mongodb-root-password`: contraseña administrativa, luego crear usuario limitado.
- `neo4j-auth`: línea `neo4j/<contraseña>`; construir fuera de Terraform.
- `postgres-password`: contraseña de metadatos.
- `airflow-db-uri`: URI `postgresql+psycopg2://airflow:<password-url-encoded>@postgres/airflow`.
- `airflow-fernet-key`: clave Fernet válida, generada por el operador fuera del repo.
- `airflow-web-key`: clave de sesión compartida scheduler/webserver.

No imprimir secretos en consola ni usar contraseñas en argumentos. Compose
secrets usa archivos, no es un vault cifrado: restringir ACL en Windows y modo
0600 en Linux. Un cambio de contraseña no rota automáticamente usuarios en
volúmenes existentes. Nunca usar `down -v` como rutina de parada.

## Inicio local verificado

Desde raíz con Docker Desktop Linux containers; validado con límite ~8GiB y arranque escalonado. Comandos completos y PowerShell en README raíz. Solo este proyecto:

```powershell
docker compose config --quiet
docker compose build runner airflow-init
docker compose up -d --wait mongodb cassandra neo4j postgres --wait-timeout 360
docker compose run --rm airflow-init
docker compose run --rm --no-deps airflow-init python /opt/project/scripts/airflow_admin.py
docker compose --profile web up -d api dashboard airflow-scheduler airflow-webserver
docker compose ps
docker compose stop
```

Existe DAG real de7 etapas, fuentes NVD locales, streaming ijson. Durante carga completa detener opcionalmente scheduler/webserver de este proyecto para liberar RAM. Checkpoints en volumen `checkpoint_data` y dedup temporal en disco contenedor, evitando I/O SQLite aleatorio sobre bind Windows. No iniciar CLI/DAG simultáneamente. Puertos web18000/18501/18080; ningún motor publicado.

## Requisitos previos a Compose GCP (bloqueo explícito)

No se proporciona un overlay que publique bases sin protección. Antes de
integrar Cloud Run es obligatorio preparar y probar:

1. MongoDB `requireTLS`, certificados CA y SAN del host privado; usuario de
   aplicación limitado y SCRAM, nunca utilizar root desde servicios.
2. Cassandra `PasswordAuthenticator`, `CassandraAuthorizer`, usuario propio,
   eliminar credencial predeterminada y habilitar `client_encryption_options`
   con `enabled: true`, `optional: false`, keystore y truststore montados.
   El arranque inicial con credenciales por defecto ocurre solo aislado.
3. Neo4j Bolt `server.bolt.tls_level=REQUIRED`, política SSL Bolt con certificado
   y clave montados, permisos mínimos disponibles en Community (limitaciones
   de RBAC respecto a Enterprise). No exponer HTTP 7474.
4. Clientes con verificación de CA y hostname; no `trust all`, no TLS opcional.
5. Publicar 27017/9042/7687 exclusivamente en IP privada de VM, enlazada al
   firewall Direct VPC. Para administración usar IAP SSH y túneles.
6. Reemplazar volúmenes nombrados por bind mounts bajo `/srv/ti-data/`, también
   PostgreSQL y logs Airflow, con UID/permisos correctos y backups probados.
7. Añadir red de salida para Airflow y probar acceso GCS sin credenciales JSON.

Estos son pendientes reales, no controles ya implementados. Terraform prepara
la red, pero no configura procesos dentro de contenedores ni los inicia.
Dockerfile Python incluye app y dependencias bloqueadas; eso no soluciona los bloqueos TLS/IAM anteriores. No desplegar Compose local en GCP sin aprobación y hardening.
