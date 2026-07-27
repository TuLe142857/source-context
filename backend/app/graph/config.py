from pydantic_settings import BaseSettings
from pydantic import SecretStr, computed_field
from functools import lru_cache

from neo4j import GraphDatabase, AsyncGraphDatabase, Driver, AsyncDriver


class GraphSettings(BaseSettings):
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: SecretStr = SecretStr("changethis")

    NEO4J_PORT: int = 7687
    NEO4J_HOST: str = "neo4j"

    @computed_field
    @property
    def NEO4J_URI(self) -> str:
        return f"bolt://{self.NEO4J_USER}:{self.NEO4J_PASSWORD.get_secret_value()}@{self.NEO4J_HOST}:{self.NEO4J_PORT}"


@lru_cache
def get_graph_settings() -> GraphSettings:
    return GraphSettings()


@lru_cache
def get_driver() -> Driver:
    return GraphDatabase.driver(
        get_graph_settings().NEO4J_URI,
    )


@lru_cache
def get_async_driver() -> AsyncDriver:
    return AsyncGraphDatabase.driver(
        get_graph_settings().NEO4J_URI,
    )
