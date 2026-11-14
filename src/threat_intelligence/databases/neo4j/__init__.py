from neo4j import GraphDatabase


class Neo:
    def __init__(self, config):
        self.driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_username, config.neo4j_password),
            connection_timeout=10,
            max_transaction_retry_time=20,
        )
        self.database = config.neo4j_database

    def query(self, text, **params):
        with self.driver.session(database=self.database) as session:
            return session.run(text, **params).data()

    def initialize(self):
        for label, key in (
            ("CVE", "id"),
            ("CWE", "id"),
            ("Product", "id"),
            ("Vendor", "id"),
            ("CPE", "id"),
            ("Reference", "url"),
        ):
            self.query(
                f"CREATE CONSTRAINT {label.lower()}_unique IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
            )

    def write(self, rows, old=None):
        rows = [{k: v for k, v in row.items() if k != "raw_cve"} for row in rows]

        def transaction(tx):
            tx.run(
                "UNWIND $rows AS row MERGE (c:CVE {id:row.cve_id}) SET c.description=row.description, c.severity=row.severity, c.content_hash=row.content_hash, c.last_modified=row.last_modified WITH c OPTIONAL MATCH (c)-[r]->() DELETE r",
                rows=rows,
            ).consume()
            tx.run(
                "UNWIND $rows AS row MATCH (c:CVE {id:row.cve_id}) UNWIND row.cwes AS id MERGE (w:CWE {id:id}) MERGE (c)-[:CLASSIFIED_AS]->(w)",
                rows=rows,
            ).consume()
            tx.run(
                "UNWIND $rows AS row MATCH (c:CVE {id:row.cve_id}) UNWIND row.products AS p MERGE (v:Vendor {id:p.vendor}) MERGE (n:Product {id:p.id}) SET n.name=p.product, n.part=p.part MERGE (n)-[:PRODUCED_BY]->(v) MERGE (c)-[:AFFECTS]->(n)",
                rows=rows,
            ).consume()
            tx.run(
                "UNWIND $rows AS row MATCH (c:CVE {id:row.cve_id}) UNWIND row.cpes AS p MERGE (n:CPE {id:p.criteria}) MERGE (c)-[:AFFECTS_CPE]->(n) WITH n,p MATCH (product:Product {id:p.product_id}) MERGE (n)-[:IDENTIFIES]->(product)",
                rows=rows,
            ).consume()
            tx.run(
                "UNWIND $rows AS row MATCH (c:CVE {id:row.cve_id}) UNWIND row.references AS url MERGE (r:Reference {url:url}) MERGE (c)-[:REFERENCES]->(r)",
                rows=rows,
            ).consume()

        # Raw CVE is kept in Mongo, not repeated as a graph property.
        with self.driver.session(database=self.database) as session:
            session.execute_write(transaction)

    def ping(self):
        self.driver.verify_connectivity()

    def count(self):
        return self.query("MATCH (c:CVE) RETURN count(c) AS n")[0]["n"]

    def close(self):
        self.driver.close()
