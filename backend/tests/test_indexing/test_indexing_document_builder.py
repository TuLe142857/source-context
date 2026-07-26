"""Tests for provider-neutral indexing document generation."""

import json
from dataclasses import replace

import pytest

from app.chunking import (
    ChunkCoverage,
    ChunkedSourceFile,
    ChunkingOptions,
    ChunkingResult,
    RepositoryChunkingBatch,
    SourceChunk,
)
from app.domain.source_file import (
    compute_source_content_hash,
)
from app.indexing import (
    IndexDeleteReason,
    IndexingContractError,
    IndexingDocumentBuilder,
)
from app.parser.repository_contracts import (
    SourceFileChange,
    SourceFileFingerprint,
)


def make_changed_batch(
    *,
    file_path: str = "src/service.py",
    source: str = "value = 1\n",
    change: SourceFileChange = (SourceFileChange.ADDED),
) -> RepositoryChunkingBatch:
    """Create one exact repository chunking fixture."""

    source_bytes = source.encode(
        "utf-8",
    )
    content_hash = compute_source_content_hash(
        source_bytes,
    )

    chunk = SourceChunk(
        index=0,
        file_path=file_path,
        language="python",
        parser_name="python",
        start_byte=0,
        end_byte=len(source_bytes),
        size=len(source_bytes),
        content=source,
        symbol_name="value",
        symbol_kind="variable",
    )

    coverage = ChunkCoverage(
        total_bytes=len(source_bytes),
        covered_bytes=len(source_bytes),
        missing_bytes=0,
        overlap_bytes=0,
        issues=(),
    )

    options = ChunkingOptions(
        max_size=100,
    )

    chunking_result = ChunkingResult(
        file_path=file_path,
        language="python",
        parser_name="python",
        options=options,
        chunks=(chunk,),
        coverage=coverage,
    )

    chunked_file = ChunkedSourceFile(
        relative_path=file_path,
        content_hash=content_hash,
        change=change,
        chunking_result=chunking_result,
    )

    return RepositoryChunkingBatch(
        chunked_files=(chunked_file,),
        unchanged_paths=(),
        deleted_paths=(),
        current_files=(
            SourceFileFingerprint(
                relative_path=file_path,
                content_hash=content_hash,
            ),
        ),
    )


def test_builder_creates_document_and_replace_operation() -> None:
    batch = make_changed_batch()

    plan = IndexingDocumentBuilder().build(
        batch,
        repository_id="repository-1",
        revision="abc123",
    )

    assert plan.document_count == 1
    assert plan.delete_operation_count == 1
    assert plan.has_operations is True

    document = plan.documents[0]

    assert (
        len(
            document.document_id,
        )
        == 64
    )

    assert document.repository_id == ("repository-1")
    assert document.revision == "abc123"
    assert document.file_path == ("src/service.py")
    assert document.text == "value = 1\n"
    assert document.chunk_index == 0
    assert document.language == "python"
    assert document.parser_name == "python"
    assert document.source_change == "added"
    assert document.symbol_name == "value"
    assert document.symbol_kind == "variable"

    delete_operation = plan.delete_operations[0]

    assert delete_operation.file_path == ("src/service.py")
    assert delete_operation.reason is IndexDeleteReason.REPLACE_FILE


def test_document_id_is_stable_across_revisions() -> None:
    batch = make_changed_batch()

    first_plan = IndexingDocumentBuilder().build(
        batch,
        repository_id="repository-1",
        revision="revision-a",
    )

    second_plan = IndexingDocumentBuilder().build(
        batch,
        repository_id="repository-1",
        revision="revision-b",
    )

    assert first_plan.documents[0].document_id == second_plan.documents[0].document_id

    assert first_plan.documents[0].revision == "revision-a"
    assert second_plan.documents[0].revision == "revision-b"


def test_deleted_file_creates_delete_only_plan() -> None:
    batch = RepositoryChunkingBatch(
        chunked_files=(),
        unchanged_paths=(),
        deleted_paths=("src/deleted.py",),
        current_files=(),
    )

    plan = IndexingDocumentBuilder().build(
        batch,
        repository_id="repository-1",
        revision="abc123",
    )

    assert plan.documents == ()
    assert plan.changed_paths == ()
    assert plan.deleted_paths == ("src/deleted.py",)
    assert plan.has_operations is True

    assert plan.delete_operations[0].reason is IndexDeleteReason.SOURCE_DELETED


def test_unchanged_only_batch_has_no_operations() -> None:
    content_hash = compute_source_content_hash(
        b"value = 1\n",
    )

    batch = RepositoryChunkingBatch(
        chunked_files=(),
        unchanged_paths=("src/stable.py",),
        deleted_paths=(),
        current_files=(
            SourceFileFingerprint(
                relative_path=("src/stable.py"),
                content_hash=content_hash,
            ),
        ),
    )

    plan = IndexingDocumentBuilder().build(
        batch,
        repository_id="repository-1",
        revision="abc123",
    )

    assert plan.documents == ()
    assert plan.delete_operations == ()
    assert plan.changed_paths == ()
    assert plan.unchanged_paths == ("src/stable.py",)
    assert plan.has_operations is False


def test_builder_rejects_chunk_path_mismatch() -> None:
    batch = make_changed_batch()

    chunked_file = batch.chunked_files[0]
    chunking_result = chunked_file.chunking_result
    chunk = chunking_result.chunks[0]

    invalid_chunk = replace(
        chunk,
        file_path="src/other.py",
    )

    invalid_result = replace(
        chunking_result,
        chunks=(invalid_chunk,),
    )

    invalid_file = replace(
        chunked_file,
        chunking_result=invalid_result,
    )

    invalid_batch = replace(
        batch,
        chunked_files=(invalid_file,),
    )

    with pytest.raises(
        IndexingContractError,
        match="Chunk file path",
    ):
        IndexingDocumentBuilder().build(
            invalid_batch,
            repository_id="repository-1",
            revision="abc123",
        )


def test_plan_is_json_serializable() -> None:
    batch = make_changed_batch()

    plan = IndexingDocumentBuilder().build(
        batch,
        repository_id="repository-1",
        revision="abc123",
    )

    payload = plan.to_dict(
        include_text=True,
    )

    serialized = json.dumps(
        payload,
    )

    assert '"document_count": 1' in serialized
    assert '"text": "value = 1\\n"' in serialized


@pytest.mark.parametrize(
    (
        "repository_id",
        "revision",
        "expected_message",
    ),
    [
        (
            "",
            "abc123",
            "repository_id",
        ),
        (
            "repository-1",
            "",
            "revision",
        ),
    ],
)
def test_builder_rejects_empty_context(
    repository_id: str,
    revision: str,
    expected_message: str,
) -> None:
    batch = make_changed_batch()

    with pytest.raises(
        IndexingContractError,
        match=expected_message,
    ):
        IndexingDocumentBuilder().build(
            batch,
            repository_id=repository_id,
            revision=revision,
        )
