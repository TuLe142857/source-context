"""Exact source-coverage validation for generated chunks."""

from collections.abc import Sequence

from .contracts import (
    ChunkCoverage,
    SourceChunk,
)
from .size import ChunkSizeMeasurer


def verify_chunk_coverage(
    chunks: Sequence[SourceChunk],
    source_bytes: bytes,
    *,
    max_size: int,
    measurer: ChunkSizeMeasurer,
) -> ChunkCoverage:
    """Verify ordering, ranges, content and exact byte coverage."""

    total_bytes = len(
        source_bytes,
    )
    issues: list[str] = []

    if not chunks:
        if total_bytes == 0:
            return ChunkCoverage(
                total_bytes=0,
                covered_bytes=0,
                missing_bytes=0,
                overlap_bytes=0,
                issues=(),
            )

        return ChunkCoverage(
            total_bytes=total_bytes,
            covered_bytes=0,
            missing_bytes=total_bytes,
            overlap_bytes=0,
            issues=("No chunks were emitted for a non-empty source.",),
        )

    cursor = 0
    missing_bytes = 0
    overlap_bytes = 0
    rebuilt_parts: list[bytes] = []
    previous_start = -1

    for expected_index, chunk in enumerate(
        chunks,
    ):
        if chunk.index != expected_index:
            issues.append(
                "Chunk index mismatch: "
                f"expected {expected_index}, "
                f"received {chunk.index}.",
            )

        if chunk.start_byte < previous_start:
            issues.append(
                f"Chunks are not ordered by start_byte at chunk {chunk.index}.",
            )

        previous_start = chunk.start_byte

        if (
            chunk.start_byte < 0
            or chunk.end_byte > total_bytes
            or chunk.end_byte <= chunk.start_byte
        ):
            issues.append(
                "Chunk has an invalid source range: "
                f"chunk={chunk.index}, "
                f"range={chunk.start_byte}-{chunk.end_byte}, "
                f"source_size={total_bytes}.",
            )

        valid_start = max(
            0,
            min(
                chunk.start_byte,
                total_bytes,
            ),
        )
        valid_end = max(
            valid_start,
            min(
                chunk.end_byte,
                total_bytes,
            ),
        )

        if valid_start > cursor:
            missing_bytes += valid_start - cursor
            issues.append(
                f"Gap before chunk {chunk.index}: {cursor}-{valid_start}.",
            )
        elif valid_start < cursor:
            overlap = max(
                0,
                min(
                    cursor,
                    valid_end,
                )
                - valid_start,
            )
            overlap_bytes += overlap

            if overlap:
                issues.append(
                    "Overlap at chunk "
                    f"{chunk.index}: "
                    f"{valid_start}-"
                    f"{min(cursor, valid_end)}.",
                )

        cursor = max(
            cursor,
            valid_end,
        )

        source_slice = source_bytes[valid_start:valid_end]
        rebuilt_parts.append(
            source_slice,
        )

        expected_content = source_slice.decode(
            "utf-8",
            errors="replace",
        )

        if chunk.content != expected_content:
            issues.append(
                "Chunk content does not match its "
                f"source range at chunk {chunk.index}.",
            )

        measured_size = measurer.measure(
            source_slice,
        )

        if chunk.size != measured_size:
            issues.append(
                "Chunk size metadata mismatch at "
                f"chunk {chunk.index}: "
                f"expected {measured_size}, "
                f"received {chunk.size}.",
            )

        if measured_size > max_size:
            issues.append(
                "Chunk exceeds max_size at "
                f"chunk {chunk.index}: "
                f"{measured_size} > {max_size}.",
            )

    if cursor < total_bytes:
        missing_bytes += total_bytes - cursor
        issues.append(
            f"Trailing gap: {cursor}-{total_bytes}.",
        )

    rebuilt_source = b"".join(
        rebuilt_parts,
    )

    if rebuilt_source != source_bytes:
        issues.append(
            "Concatenating chunk byte ranges does not rebuild the source.",
        )

    return ChunkCoverage(
        total_bytes=total_bytes,
        covered_bytes=(total_bytes - missing_bytes),
        missing_bytes=missing_bytes,
        overlap_bytes=overlap_bytes,
        issues=tuple(
            issues,
        ),
    )
