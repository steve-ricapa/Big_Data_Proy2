# Demo universitaria vigente — Cassandra en tres VMs

Duración sugerida: 8–10 min. No disparar el DAG, ejecutar CRUD ni detener nodos en vivo. Abrir el dashboard autenticado y el túnel de Airflow antes de proyectar; nunca mostrar credenciales.

1. **Arquitectura (1 min).** Mostrar el [Mermaid vigente](../architecture/cassandra-gcp-cluster.md): NVD → Airflow → MongoDB, Cassandra y Neo4j → API → dashboard/MCP. Solo Cassandra está distribuida. Confirmar las tres VMs desde el proyecto autorizado:

   ```bash
   gcloud compute instances list --project=proyectobigdata2-514216 --format='table(name,zone.basename(),networkInterfaces[0].networkIP,status)'
   python scripts/gcp_remote.py --command 'sudo docker exec threat-intelligence-cassandra-1 nodetool status threat_intelligence'
   ```

2. **Cassandra (2 min).** Mostrar `UN`, el DC `dc1`, los tres racks y 16 vnodes por host. `rack1` representa la zona `us-central1-a`. Los tokens ordenan el anillo y asignan rangos; RF=3 guarda tres réplicas y `LOCAL_QUORUM` exige dos. Los seeds ayudan a descubrir pares, no son maestros. Mostrar `failover-02.txt` y `failover-03.txt` del [directorio de evidencias](../evidence/cassandra_cluster/), con `DN`, las operaciones de quorum y el regreso a `UN`.
3. **DAG (1–2 min).** Abrir la UI mediante túnel IAP hacia el puerto 18081. Mostrar las siete tareas del `nvd_threat_intelligence`, el último run completo y sus etapas. Alternativa: [manifiesto de cierre](../evidence/final_closure/etl.json).
4. **Motores y dashboard (3 min).** En `https://ti-136-114-21-18.sslip.io`, recorrer Overview, Explorer (documento MongoDB), Threat Analytics (snapshot Cassandra), Graph Intelligence (Neo4j; `CVE-2021-44228`) y Data Pipeline. Mostrar cinco indicadores con el `as_of` que devuelve la API: total, severidad, promedio CVSS por versión, modificados en 30 días y productos identificables. Usar [fórmulas](../kpis/catalog.md), no sustituir el dato vivo por un corte antiguo. Para CRUD, mostrar [`crud.json`](../evidence/cassandra_cluster/crud.json) y [`neo4j-relationship-crud.json`](../evidence/cassandra_cluster/neo4j-relationship-crud.json).
5. **MCP y conclusión (1 min).** Opcional si el dueño ya tiene sesión de Codex. Si no, usar la [evidencia real de las seis herramientas](../evidence/final_closure/mcp-stdio.json) y no llamarla prueba OAuth. Concluir que Cassandra tolera la pérdida de un nodo, pero el resto de la plataforma depende de `ti-dev-data`.

**Plan B:** abrir con antelación el [runtime del cierre](../evidence/final_closure/runtime.txt), manifiesto ETL y capturas históricas del [dashboard](../evidence/technical_closure/screenshots/). Las capturas son del 16/11, no del nuevo corte.
