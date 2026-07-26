"""Tests for chunking contracts, size measurement and coverage."""

import json

import pytest

from app.chunking import (
    ChunkingOptions,
    ChunkingResult,
    ChunkSizeUnit,
    SourceChunk,
    get_size_measurer,
    measure_source_range,
    verify_chunk_coverage,
)


def make_chunk(
    source_bytes: bytes,
    *,
    index: int,
    start_byte: int,
    end_byte: int,
    unit: ChunkSizeUnit = ChunkSizeUnit.BYTE,
) -> SourceChunk:
    """Create a source chunk matching one exact source range."""

    source_slice = source_bytes[start_byte:end_byte]
    measurer = get_size_measurer(
        unit,
    )

    return SourceChunk(
        index=index,
        file_path="src/service.py",
        language="python",
        parser_name="python",
        start_byte=start_byte,
        end_byte=end_byte,
        size=measurer.measure(
            source_slice,
        ),
        content=source_slice.decode(
            "utf-8",
            errors="replace",
        ),
    )


def test_chunking_options_reject_non_positive_size() -> None:
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ChunkingOptions(
            max_size=0,
        )


def test_byte_size_counts_utf8_bytes() -> None:
    source_bytes = "Tổng".encode(
        "utf-8",
    )

    measurer = get_size_measurer(
        ChunkSizeUnit.BYTE,
    )

    assert measurer.measure(
        source_bytes,
    ) == len(source_bytes)
    assert len(source_bytes) > len("Tổng")


def test_word_size_matches_whitespace_separated_words() -> None:
    source_bytes = ("one  two\nthree\tfour").encode(
        "utf-8",
    )

    measurer = get_size_measurer(
        ChunkSizeUnit.WORD,
    )

    assert (
        measurer.measure(
            source_bytes,
        )
        == 4
    )


def test_measure_source_range_validates_boundaries() -> None:
    source_bytes = b"abcdef"
    measurer = get_size_measurer(
        ChunkSizeUnit.BYTE,
    )

    assert (
        measure_source_range(
            source_bytes,
            start_byte=1,
            end_byte=4,
            measurer=measurer,
        )
        == 3
    )

    with pytest.raises(
        ValueError,
        match="Invalid source byte range",
    ):
        measure_source_range(
            source_bytes,
            start_byte=-1,
            end_byte=4,
            measurer=measurer,
        )


def test_exact_chunks_rebuild_unicode_source() -> None:
    source_bytes = ('message = "Tổng"\nprint(message)\n').encode(
        "utf-8",
    )

    split_byte = (
        source_bytes.index(
            b"\n",
        )
        + 1
    )

    chunks = (
        make_chunk(
            source_bytes,
            index=0,
            start_byte=0,
            end_byte=split_byte,
        ),
        make_chunk(
            source_bytes,
            index=1,
            start_byte=split_byte,
            end_byte=len(source_bytes),
        ),
    )

    measurer = get_size_measurer(
        ChunkSizeUnit.BYTE,
    )

    coverage = verify_chunk_coverage(
        chunks,
        source_bytes,
        max_size=len(source_bytes),
        measurer=measurer,
    )

    assert coverage.is_exact is True
    assert coverage.covered_bytes == len(
        source_bytes,
    )
    assert coverage.missing_bytes == 0
    assert coverage.overlap_bytes == 0
    assert coverage.issues == ()


def test_coverage_detects_gap() -> None:
    source_bytes = b"abcdef"

    chunks = (
        make_chunk(
            source_bytes,
            index=0,
            start_byte=0,
            end_byte=2,
        ),
        make_chunk(
            source_bytes,
            index=1,
            start_byte=3,
            end_byte=6,
        ),
    )

    coverage = verify_chunk_coverage(
        chunks,
        source_bytes,
        max_size=10,
        measurer=get_size_measurer(
            ChunkSizeUnit.BYTE,
        ),
    )

    assert coverage.is_exact is False
    assert coverage.missing_bytes == 1
    assert coverage.overlap_bytes == 0
    assert any(issue.startswith("Gap") for issue in coverage.issues)


def test_coverage_detects_overlap() -> None:
    source_bytes = b"abcdef"

    chunks = (
        make_chunk(
            source_bytes,
            index=0,
            start_byte=0,
            end_byte=4,
        ),
        make_chunk(
            source_bytes,
            index=1,
            start_byte=3,
            end_byte=6,
        ),
    )

    coverage = verify_chunk_coverage(
        chunks,
        source_bytes,
        max_size=10,
        measurer=get_size_measurer(
            ChunkSizeUnit.BYTE,
        ),
    )

    assert coverage.is_exact is False
    assert coverage.missing_bytes == 0
    assert coverage.overlap_bytes == 1
    assert any(issue.startswith("Overlap") for issue in coverage.issues)


def test_coverage_detects_content_and_size_mismatch() -> None:
    source_bytes = b"abcdef"

    chunk = SourceChunk(
        index=0,
        file_path="src/service.py",
        language="python",
        parser_name="python",
        start_byte=0,
        end_byte=6,
        size=999,
        content="wrong",
    )

    coverage = verify_chunk_coverage(
        (chunk,),
        source_bytes,
        max_size=3,
        measurer=get_size_measurer(
            ChunkSizeUnit.BYTE,
        ),
    )

    assert coverage.is_exact is False
    assert any("content does not match" in issue for issue in coverage.issues)
    assert any("size metadata mismatch" in issue for issue in coverage.issues)
    assert any("exceeds max_size" in issue for issue in coverage.issues)


def test_empty_source_has_exact_empty_coverage() -> None:
    coverage = verify_chunk_coverage(
        (),
        b"",
        max_size=10,
        measurer=get_size_measurer(
            ChunkSizeUnit.BYTE,
        ),
    )

    assert coverage.is_exact is True
    assert coverage.total_bytes == 0


def test_result_summary_excludes_content_by_default() -> None:
    source_bytes = b"value = 1\n"

    chunk = make_chunk(
        source_bytes,
        index=0,
        start_byte=0,
        end_byte=len(source_bytes),
    )

    options = ChunkingOptions(
        max_size=100,
    )

    coverage = verify_chunk_coverage(
        (chunk,),
        source_bytes,
        max_size=options.max_size,
        measurer=get_size_measurer(
            options.size_unit,
        ),
    )

    result = ChunkingResult(
        file_path="src/service.py",
        language="python",
        parser_name="python",
        options=options,
        chunks=(chunk,),
        coverage=coverage,
    )

    payload = result.to_dict()

    assert payload["chunk_count"] == 1
    assert payload["over_limit_count"] == 0

    chunk_payload = payload["chunks"]

    assert isinstance(
        chunk_payload,
        list,
    )
    assert "content" not in chunk_payload[0]

    serialized = json.dumps(
        payload,
    )

    assert '"is_exact": true' in serialized
