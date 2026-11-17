"""Neo4j database initialization and schema constraint management."""

import logging
from neomodel import db

logger = logging.getLogger(__name__)

NEO4J_SCHEMA_STATEMENTS: list[str] = [
    # Unique constraints
    "CREATE CONSTRAINT node_uid_unique IF NOT EXISTS FOR (n:Node) REQUIRE n.uid IS UNIQUE",
    "CREATE CONSTRAINT file_uid_unique IF NOT EXISTS FOR (f:File) REQUIRE f.uid IS UNIQUE",
    "CREATE CONSTRAINT project_uid_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.uid IS UNIQUE",
    "CREATE CONSTRAINT branch_uid_unique IF NOT EXISTS FOR (b:Branch) REQUIRE b.uid IS UNIQUE",
    "CREATE CONSTRAINT repo_uid_unique IF NOT EXISTS FOR (r:Repository) REQUIRE r.uid IS UNIQUE",
    "CREATE CONSTRAINT workspace_uid_unique IF NOT EXISTS FOR (w:Workspace) REQUIRE w.uid IS UNIQUE",
    # Performance indexes
    "CREATE INDEX node_file_uid_idx IF NOT EXISTS FOR (n:Node) ON (n.file_node_uid)",
    "CREATE INDEX node_name_idx IF NOT EXISTS FOR (n:Node) ON (n.name)",
]


def ensure_neo4j_schema() -> None:
    """Ensures required unique constraints and performance indexes exist in Neo4j.

    Executes idempotent Cypher statements to establish constraints on UID properties
    and secondary indexes for graph queries and traversals.
    """
    for stmt in NEO4J_SCHEMA_STATEMENTS:
        try:
            db.cypher_query(stmt)
        except Exception as exc:
            logger.warning(
                "Failed executing Neo4j schema statement '%s': %s",
                stmt,
                exc,
            )
    logger.info("Neo4j schema constraints and indexes verified.")
