"""Chunk-size measurement strategies."""

import re
from collections.abc import Mapping
from typing import Final, Protocol

from .contracts import ChunkSizeUnit


_WORD_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\S+",
)


class ChunkSizeMeasurer(Protocol):
    """Measure the configured size of source bytes."""

    unit: ChunkSizeUnit

    def measure(
        self,
        source_bytes: bytes,
    ) -> int:
        """Return the measured size of source bytes."""


class ByteSizeMeasurer:
    """Measure source size in raw UTF-8 bytes."""

    unit = ChunkSizeUnit.BYTE

    def measure(
        self,
        source_bytes: bytes,
    ) -> int:
        """Return the number of source bytes."""

        return len(source_bytes)


class WordSizeMeasurer:
    """Measure whitespace-separated words."""

    unit = ChunkSizeUnit.WORD

    def measure(
        self,
        source_bytes: bytes,
    ) -> int:
        """Return the number of whitespace-separated words."""

        source_text = source_bytes.decode(
            "utf-8",
            errors="replace",
        )

        return len(
            _WORD_PATTERN.findall(
                source_text,
            ),
        )


_SIZE_MEASURERS: Final[
    Mapping[
        ChunkSizeUnit,
        ChunkSizeMeasurer,
    ]
] = {
    ChunkSizeUnit.BYTE: ByteSizeMeasurer(),
    ChunkSizeUnit.WORD: WordSizeMeasurer(),
}


def get_size_measurer(
    unit: ChunkSizeUnit,
) -> ChunkSizeMeasurer:
    """Return the measurer registered for a size unit."""

    return _SIZE_MEASURERS[unit]


def measure_source_range(
    source_bytes: bytes,
    *,
    start_byte: int,
    end_byte: int,
    measurer: ChunkSizeMeasurer,
) -> int:
    """Measure one validated byte range."""

    if start_byte < 0 or end_byte < start_byte or end_byte > len(source_bytes):
        raise ValueError(
            f"Invalid source byte range: {start_byte}-{end_byte}",
        )

    return measurer.measure(
        source_bytes[start_byte:end_byte],
    )
