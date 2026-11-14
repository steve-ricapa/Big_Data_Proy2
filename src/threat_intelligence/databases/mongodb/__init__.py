from pymongo import ASCENDING, MongoClient, ReplaceOne


class Mongo:
    def __init__(self, config):
        self.client = MongoClient(
            config.mongodb_uri,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=60000,
        )
        self.db = self.client[config.mongodb_database]
        self.collection = self.db.cves

    def initialize(self):
        if "cves" not in self.db.list_collection_names():
            self.db.create_collection(
                "cves",
                validator={
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": [
                            "cve_id",
                            "content_hash",
                            "published",
                            "last_modified",
                        ],
                        "properties": {
                            "cve_id": {
                                "bsonType": "string",
                                "pattern": "^CVE-[0-9]{4}-[0-9]{4,19}$",
                            }
                        },
                    }
                },
            )
        self.collection.create_index("cve_id", unique=True)
        for key in ("last_modified", "month", "severity", "cwes", "products.id"):
            self.collection.create_index([(key, ASCENDING)])
        # Explorer filters publication year/date, not the year embedded in CVE ID.
        self.collection.create_index([("year", ASCENDING), ("cve_id", ASCENDING)])
        self.collection.create_index([("published", ASCENDING), ("cve_id", ASCENDING)])
        self.collection.create_index([("description", "text")], name="description_text")

    def write(self, rows, old=None):
        self.collection.bulk_write(
            [ReplaceOne({"cve_id": row["cve_id"]}, row, upsert=True) for row in rows],
            ordered=True,
        )

    def ping(self):
        self.client.admin.command("ping")

    def count(self):
        return self.collection.count_documents({})

    def close(self):
        self.client.close()
