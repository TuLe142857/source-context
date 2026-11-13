from unittest.mock import Mock

import pytest

from app.core.qdrant import QdrantVectorStore
from app.embedding.utils import EnrichedNodeData


def _node() -> EnrichedNodeData:
    return EnrichedNodeData(
        workspace_id=1,
        branch_id=2,
        node_id="node-1",
        project_id=3,
        start_byte=10,
        end_byte=40,
        node_type="function",
        kind="function",
        name="example",
        file_path="src/example.py",
        signature="example()",
        source_code="def example(): pass",
        docstring=None,
        embedding=[0.1, 0.2],
    )


def test_upsert_batch_is_idempotent_for_same_node_id() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [
        Mock(name="test_collection")
    ]
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    assert store.upsert_batch([_node()]) == 1
    first_point = client.upsert.call_args.kwargs["points"][0]
    node_from_retry = _node()
    node_from_retry.node_id = "random-id-from-reparse"
    assert store.upsert_batch([node_from_retry]) == 1
    second_point = client.upsert.call_args.kwargs["points"][0]

    assert first_point.id == second_point.id


def test_point_identity_is_scoped_to_workspace() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [
        Mock(name="test_collection")
    ]
    store = QdrantVectorStore(client=client, collection_name="test_collection")
    first_target = _node()
    other_workspace = _node()
    other_workspace.workspace_id = 9

    store.upsert_batch([first_target, other_workspace])
    points = client.upsert.call_args.kwargs["points"]

    assert points[0].id != points[1].id


def test_upsert_batch_propagates_qdrant_failure() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [
        Mock(name="test_collection")
    ]
    client.upsert.side_effect = RuntimeError("qdrant unavailable")
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    with pytest.raises(RuntimeError, match="qdrant unavailable"):
        store.upsert_batch([_node()])


def test_ensure_collection_propagates_qdrant_failure() -> None:
    client = Mock()
    client.get_collections.side_effect = RuntimeError("qdrant unavailable")
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    with pytest.raises(RuntimeError, match="qdrant unavailable"):
        store.ensure_collection()


def test_delete_file_filters_by_indexing_target() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [Mock(name="test_collection")]
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    store.delete_file(
        workspace_id=1,
        branch_id=2,
        project_id=3,
        file_path="src/example.py",
    )

    selector = client.delete.call_args.kwargs["points_selector"]
    conditions = {condition.key: condition.match.value for condition in selector.filter.must}
    assert conditions == {
        "workspace_id": 1,
        "branch_id": 2,
        "project_id": 3,
        "file_path": "src/example.py",
    }


def test_delete_file_creates_missing_collection_before_reconciliation() -> None:
    client = Mock()
    client.get_collections.return_value.collections = []
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    store.delete_file(
        workspace_id=1,
        branch_id=2,
        project_id=3,
        file_path="src/example.py",
    )

    client.create_collection.assert_called_once()
    client.delete.assert_called_once()


def test_replace_file_removes_obsolete_points() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [Mock(name="test_collection")]
    def scroll(**_kwargs):
        current_id = client.upsert.call_args.kwargs["points"][0].id
        return (
            [
                Mock(id=current_id, payload={"file_path": "src/example.py"}),
                Mock(id="old-id", payload={"file_path": "src/example.py"}),
            ],
            None,
        )

    client.scroll.side_effect = scroll
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    assert store.replace_file(
        [_node()],
        workspace_id=1,
        branch_id=2,
        project_id=3,
        file_path="src/example.py",
    ) == 1

    assert client.delete.call_args.kwargs["points_selector"] == ["old-id"]


def test_replace_file_empty_result_deletes_all_existing_points() -> None:
    client = Mock()
    client.get_collections.return_value.collections = []
    client.scroll.return_value = ([Mock(id="old-id", payload=None)], None)
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    assert store.replace_file(
        [],
        workspace_id=1,
        branch_id=2,
        project_id=3,
        file_path="src/example.py",
    ) == 0

    assert client.delete.call_args.kwargs["points_selector"] == ["old-id"]


def test_replace_file_rejects_mixed_targets() -> None:
    client = Mock()
    store = QdrantVectorStore(client=client, collection_name="test_collection")
    other_project = _node()
    other_project.project_id = 4

    with pytest.raises(ValueError, match="belong to the replacement target"):
        store.replace_file(
            [other_project],
            workspace_id=1,
            branch_id=2,
            project_id=3,
            file_path=other_project.file_path,
        )


def test_reconcile_project_files_removes_only_scoped_stale_points() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [Mock(name="test_collection")]
    client.scroll.return_value = (
        [
            Mock(id="keep", payload={"file_path": "src/current.py"}),
            Mock(id="delete", payload={"file_path": "src/removed.py"}),
        ],
        None,
    )
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    store.reconcile_project_files(
        workspace_id=1,
        branch_id=2,
        project_id=3,
        current_file_paths={"src/current.py"},
    )

    client.delete.assert_called_once_with(
        collection_name="test_collection", points_selector=["delete"]
    )


def test_legacy_reconciliation_removes_only_attributable_target_points() -> None:
    client = Mock()
    client.get_collections.return_value.collections = [Mock(name="test_collection")]
    client.scroll.return_value = (
        [
            Mock(id="legacy-target", payload={"file_path": "/repo/project/a.py"}),
            Mock(id="legacy-other", payload={"file_path": "/repo/other/a.py"}),
            Mock(
                id="current-format",
                payload={"project_id": 3, "file_path": "/repo/project/a.py"},
            ),
            Mock(id="legacy-unattributed", payload={"file_path": None}),
        ],
        None,
    )
    store = QdrantVectorStore(client=client, collection_name="test_collection")

    store.reconcile_legacy_points(
        workspace_id=1,
        branch_id=2,
        project_roots={"/repo/project"},
    )

    selector = client.delete.call_args.kwargs["points_selector"]
    assert selector == ["legacy-target"]
    conditions = client.scroll.call_args.kwargs["scroll_filter"].must
    assert {condition.key: condition.match.value for condition in conditions} == {
        "workspace_id": 1,
        "branch_id": 2,
    }
