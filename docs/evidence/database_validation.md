# Validación de motores reales

## Resultado final
**MongoDB171791,Cassandra171791,Neo4j171791 CVE únicos**. Canonical171791 válidos,0 inválidos/duplicados. Paridad de todos los IDs/hashes: `1a60346f5dcdbe7ee928bc7a8cf22779abeeb2bdf23efa1f39f7c7c1c3c9fcd2`. Evidencia full_recovery.log,delivery_state.json y37 pytest PASS. Neo4j617044 nodos/1467881 relaciones;no confundir nodos con CVE. Cassandra recovery paginada confirma0 reescrituras tras fallo de COUNT(*).

## Historial de muestras
La tabla1000 siguiente es histórica,no volumen final ni pendiente actual.

10/11/2026. Proyecto Docker `threat-intelligence`, red privada sin puertos de motores publicados.

| Motor | Último volumen verificado acotado | Prueba |
|---|---:|---|
| MongoDB8.0.12 |1000 CVE|sample1000.log|
| Cassandra4.1.9 |1000 CVE|sample1000.log,cassandra_query.txt|
| Neo4j5.26.12 |1000 CVE|sample1000.log,subgrafo HTTP|

No son conteos actuales durante carga activa; etapas pueden tener distintos volúmenes. Cifras definitivas de `verify` tras carga completa. Reconciliación compara conteos y huella SHA256 de todos los pares id/hash, no solo muestra.

CRUD/cambios particiones/aristas: crud_validation.md,crud.json,incremental.json. CQL consultó partición real sin ALLOW FILTERING (`cassandra_query.txt`); grafo consultado por HTTP (`http_validation.json`). Volúmenes persistentes: mongodb_data/cassandra_data/neo4j_data/checkpoint_data. No se borró dataset para pruebas.

KPI nodos Neo4j puede incluir entidades huérfanas históricas. La huella CVE no verifica cada relación; selftest sí comprueba CWE retirado sin enlace y antigua severidad Cassandra ausente.
