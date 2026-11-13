from unittest.mock import Mock

import pytest

from app.engine.graph import persistence


def test_source_artifact_is_not_deleted_while_another_file_references_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    monkeypatch.setattr(persistence, "get_s3_client", lambda: client)
    monkeypatch.setattr(
        persistence.db,
        "cypher_query",
        lambda *_args, **_kwargs: ([[1]], None),
    )

    persistence.delete_source_artifacts({"source_code_file/shared.py"})

    client.delete_object.assert_not_called()


def test_unreferenced_source_artifact_is_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    monkeypatch.setattr(persistence, "get_s3_client", lambda: client)
    monkeypatch.setattr(
        persistence.db,
        "cypher_query",
        lambda *_args, **_kwargs: ([[0]], None),
    )

    persistence.delete_source_artifacts({"source_code_file/orphan.py"})

    client.delete_object.assert_called_once_with(
        Bucket=persistence.settings.S3_DEFAULT_BUCKET,
        Key="source_code_file/orphan.py",
    )


def test_source_artifact_delete_failure_propagates_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = Mock()
    client.delete_object.side_effect = RuntimeError("S3 unavailable")
    monkeypatch.setattr(persistence, "get_s3_client", lambda: client)
    monkeypatch.setattr(
        persistence.db,
        "cypher_query",
        lambda *_args, **_kwargs: ([[0]], None),
    )

    with pytest.raises(RuntimeError, match="S3 unavailable"):
        persistence.delete_source_artifacts({"source_code_file/orphan.py"})


def test_api_linking_can_join_the_callers_graph_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.engine.api_map import languages, link

    class UnexpectedTransaction:
        def __enter__(self) -> None:
            raise AssertionError("nested Neo4j transaction was opened")

        def __exit__(self, *_args: object) -> None:
            return None

    class FakeDatabase:
        transaction = UnexpectedTransaction()

        def cypher_query(self, *_args: object, **_kwargs: object) -> tuple[list, None]:
            return [], None

    monkeypatch.setattr(link, "db", FakeDatabase())
    monkeypatch.setattr(languages, "get_api_handler_registry", lambda: Mock())

    assert link.link_api_map([1], transactional=False) == 0
