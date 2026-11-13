"""Project-scoped graph replacement and source-artifact helpers."""

from collections.abc import Iterable

from neomodel import db

from app.core.config import settings
from app.core.s3 import get_s3_client
from app.engine.graph.model import ProjectNodeModel


def project_source_artifact_keys(project_id: int) -> set[str]:
    project = ProjectNodeModel.nodes.get_or_none(uid=project_id)
    if project is None:
        return set()
    return {
        file_node.source_code_key
        for file_node in project.files.all()
        if file_node.source_code_key
    }


def clear_project_graph(project_id: int) -> None:
    """Remove only file/UAST/API data owned by this project, inside caller transaction."""
    db.cypher_query(
        """
        MATCH (p:Project {uid: $project_id})
        OPTIONAL MATCH (p)-[:INCLUDES]->(f:File)
        WITH collect(DISTINCT f.uid) AS file_uids
        MATCH (n:Node)
        WHERE n.file_node_uid IN file_uids
        DETACH DELETE n
        """,
        {"project_id": project_id},
    )
    db.cypher_query(
        "MATCH (p:Project {uid: $project_id})-[:INCLUDES]->(f:File) DETACH DELETE f",
        {"project_id": project_id},
    )
    db.cypher_query(
        "MATCH (a:Api {project_id: $project_id}) DETACH DELETE a",
        {"project_id": project_id},
    )


def remove_project_files(project_id: int, relative_paths: Iterable[str]) -> None:
    paths = sorted(set(relative_paths))
    if not paths:
        return
    db.cypher_query(
        """
        MATCH (:Project {uid: $project_id})-[:INCLUDES]->(f:File)
        WHERE f.relative_path IN $paths
        WITH collect(DISTINCT f.uid) AS file_uids
        MATCH (n:Node)
        WHERE n.file_node_uid IN file_uids
        DETACH DELETE n
        """,
        {"project_id": project_id, "paths": paths},
    )
    db.cypher_query(
        """
        MATCH (:Project {uid: $project_id})-[:INCLUDES]->(f:File)
        WHERE f.relative_path IN $paths
        DETACH DELETE f
        """,
        {"project_id": project_id, "paths": paths},
    )


def clear_project_call_relationships(project_id: int) -> None:
    db.cypher_query(
        """
        MATCH (p:Project {uid: $project_id})-[:INCLUDES]->(:File)
          -[:DECLARE]->()-[:PARENT_OF*0..]->(n:Node)-[r:REFERENCE_TO]->()
        WITH DISTINCT r
        DELETE r
        """,
        {"project_id": project_id},
    )


def delete_source_artifacts(keys: Iterable[str]) -> None:
    client = get_s3_client()
    for key in set(keys):
        rows, _ = db.cypher_query(
            "MATCH (f:File {source_code_key: $key}) RETURN count(f)",
            {"key": key},
        )
        if not rows or rows[0][0] == 0:
            client.delete_object(Bucket=settings.S3_DEFAULT_BUCKET, Key=key)


def cleanup_project_artifacts(project_id: int) -> None:
    """Delete unreferenced generation objects under this project's private prefix."""
    referenced = project_source_artifact_keys(project_id)
    client = get_s3_client()
    prefix = f"source_code_file/project_{project_id}/"
    token: str | None = None
    while True:
        response = client.list_objects_v2(
            Bucket=settings.S3_DEFAULT_BUCKET,
            Prefix=prefix,
            **({"ContinuationToken": token} if token else {}),
        )
        for item in response.get("Contents", []):
            key = item["Key"]
            if key not in referenced:
                rows, _ = db.cypher_query(
                    "MATCH (f:File {source_code_key: $key}) RETURN count(f)",
                    {"key": key},
                )
                if not rows or rows[0][0] == 0:
                    client.delete_object(Bucket=settings.S3_DEFAULT_BUCKET, Key=key)
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
