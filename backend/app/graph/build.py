from app.scip import scip_pb2 as scip

import logging

def build_call_graph_for_project(project_id: int, index: scip.Index):
    """
    Use scip index result to build a call graph for a project.
    This method need the project and it's nodes(FileNode, UASTNode in file)
    saved in neo4j.

    This method search for ``ReferencesNode`` in graphdb and lookup to find it's mapped ``Occurrences``
    (by position, name, ...) in the scip index result, then create reference relation in graphdb.
    Args:
        project_id: project id for ProjectNodeModel save in neo4j
        index: scip index object for the whole project

    Returns:
        ``None``

    Notes:
        This method is template and will be implemented soon.
    """
    logger = logging.getLogger(__name__)
    logger.info("Building call graph for project was call. But this method was not implemented yet")

