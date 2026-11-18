import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    nvd_raw_dir: Path = Path("data/raw/nvd")
    staging_dir: Path = Path("data/staging")
    state_dir: Path = Path("data/processed")
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "threat_intelligence"
    cassandra_contact_points: str = "localhost"
    cassandra_port: int = 9042
    cassandra_keyspace: str = "threat_intelligence"
    cassandra_local_datacenter: str = "dc1"
    cassandra_username: str = ""
    cassandra_password: str = ""
    cassandra_create_keyspace: bool = True
    cassandra_consistency: str = "LOCAL_ONE"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    batch_size: int = 200

    def model_post_init(self, context):
        # Docker secrets take precedence without printing their contents.
        for field in ("mongodb_uri", "neo4j_password", "cassandra_password"):
            filename = os.getenv(field.upper() + "_FILE")
            if filename:
                object.__setattr__(self, field, Path(filename).read_text().strip())


@lru_cache
def settings():
    return Settings()
