# Estructuras y consultas nativas

La creación ejecutable de estructuras vive en los adaptadores `initialize()` bajo `src/threat_intelligence/databases/`: valida keyspace/DC, crea tablas CQL, índices/validator Mongo y constraints Neo4j. Cada `runner <motor> --run-dir ...` inicializa antes de escribir; no se duplica esquema en archivos SQL divergentes.

- MongoDB `cves` unique cve_id y campos requeridos; consultas de lectura en API.
- Cassandra: cuatro tablas de CVE y `kpi_snapshots`; queries parametrizadas sin ALLOW FILTERING.
- Neo4j: constraints de seis entidades, MERGE y queries parametrizadas; no plugins necesarios.

Ejemplo real Cassandra desde PowerShell:
```powershell
docker compose exec cassandra cqlsh -e "DESCRIBE KEYSPACE threat_intelligence;"
docker compose exec cassandra cqlsh -e "SELECT * FROM threat_intelligence.cves_by_cwe WHERE bucket='CWE-79' AND month='2024-01' LIMIT 5;"
```

Para Mongo/Neo4j usar runner/API con secretos de Docker; no introducir contraseñas en argumentos de shell ni publicar puertos solo para una captura. `runner crud --output docs/evidence/crud.json` demuestra operaciones nativas con IDs aislados. Modelos detallados: `docs/data_models/`.
