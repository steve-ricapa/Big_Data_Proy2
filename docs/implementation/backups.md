# Backups yrestauración

Se ejecutó `scripts/backup_local.py`: parada coordinada de escritores ydespués
los tres motores/PostgreSQL; copia fría de los volúmenes yreinicio exacto de los
servicios previamente activos. Rechaza comenzar si hay DAG queued/running.
No copiar archivos de motores activos como si fueran un snapshot consistente.

Archivo ySHA256 por volumen: `docs/evidence/backup_validation.json`.
Mongo222MB,Cassandra186MB,Neo4j211MB,PostgreSQL9.8MB,checkpoints56.6MB yauth
Airflow355bytes comprimidos. Lectura íntegra de tar/gzip verifica truncamiento/CRC.
Configuración fuente respaldada sin secretos,ADC,Terraform state ni datasets.
Los volúmenes sí contienen datos/autenticación: tratar backups como sensibles.

## Restauración aislada realmente ejecutada

`scripts/verify_backup_restore.py` verificóSHA256,extrajo Mongo a un **nuevo**
volumen yarrancóMongo8.0.12 con `--network none`,sin puertos,sin tocar el origen.
Autenticó internamente yleeyó los171791 pares ID/hash:huella exacta igual al origen.
`docs/evidence/backup_restore_validation.json`:SUCCESS. Contenedor/volumen de
prueba conservados detenidos para inspección. No afirmar que se ensayóarranque
restaurado de Cassandra/Neo4j/PostgreSQL:se respaldaron pero ese ensayo es pendiente.

## Política cloud prevista

- Backup frío diario de los motores,metadata,checkpoints yconfiguración; pequeña
  ventana de mantenimiento. Primero pausar DAG yesperar tareas,drenar escrituras.
- Restaurar con mismas versiones/configuración/credenciales privadas. No restaurar
  un backup Mongo encima de un origen vivo ni mezclar checkpoints de otra fecha.
- Guardar archivos en disco de datos yGCS privado,cifrado en reposo,sin ACLpúblicas.
- Conservar7diarios remotos bajo prefijo `backups/`;lifecycle7d ysoftdelete7d
  implican hasta14d de almacenamiento facturable. Nunca eliminar raw por retención.
- Local no hay borrado automático:el usuario pidió preservar datos. Copias locales
  manuales fuera deGit/contextoDocker,secretos respaldados por canal privado aparte.
- Un backup frío de Neo4j se restaura como árbol `/data`conla misma imagen;Cassandra
  requiere todo `/var/lib/cassandra`incluyendo system/schema/auth,configuración igual;
  PostgreSQL requiere todo PGDATA yversión compatible. Validar antes de promocionar.

El script local reconoce volúmenes de este proyecto:no usarlo para otros proyectos.
Antes de usarlo enGCP ajustar rutas/serviciosKeycloak/Caddy ydestinoGCS;la existencia
del script no acredita todavía automatización remota ni recuperación de todos motores.
