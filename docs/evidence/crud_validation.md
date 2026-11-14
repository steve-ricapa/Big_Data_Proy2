# Validación CRUD real

Ejecución local 10/11/2026: `docker compose run --rm --no-deps runner crud --output docs/evidence/crud.json`. Resultado primario: [`crud.json`](crud.json), log [`crud.log`](crud.log).

12 operaciones verificadas por aserciones: create/read/update/delete en MongoDB 8.0.12, Cassandra 4.1.9 y Neo4j 5.26.12. Cada operación se lee de vuelta; delete confirma ausencia. ID sintético único bajo CVE-2099, claramente prueba y eliminado al terminar; no se borran documentos del dataset. Cassandra CRUD puntual sobre `cves_by_id`; las tablas secundarias se validan en prueba incremental separada, no se confunde con CRUD de todas las tablas.

`src/threat_intelligence/crud.py` contiene comandos de drivers reales: `insert_one/find_one/update_one/delete_one`, CQL `INSERT/SELECT/UPDATE/DELETE`, Cypher `CREATE/MATCH/SET/DETACH DELETE`. El comando falla con estado no cero ante una aserción o indisponibilidad; no presenta mocks como integración.

Regresión incremental adicional: [`incremental.json`](incremental.json) y [`incremental.log`](incremental.log): nuevo+inválido, replay sin cambios, modificado eliminando severidad/CWE antiguos, rechazo de fecha anterior, paridad de identidad/hash. El registro sintético se limpia al final; no representa dato NVD real.
# Revalidación posterior

Suite Docker actual42PASS,incluye CRUD real de los tres motores con identidad
Mongo writer. `revalidation_incremental.json` demuestra cinco regresiones reales.
Test adicional de API Mongo: lector consulta documentos y recibe código13
Unauthorized ante INSERT. XML `revalidation_integration_tests.xml`.

## Histórico de evidencias CRUD
