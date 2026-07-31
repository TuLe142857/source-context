"""Fallback splitting for oversized source spans."""

from app.parser.uast import UASTNode

from .contracts import ChunkSizeUnit
from .size import ChunkSizeMeasurer
from .structural import SourceSpan


class FallbackSpanSplitter:
    """Split an oversized span without requiring structural children."""

    def __init__(
        self,
        *,
        max_size: int,
        measurer: ChunkSizeMeasurer,
    ) -> None:
        if max_size <= 0:
            raise ValueError(
                "max_size must be greater than zero",
            )

        self._max_size = max_size
        self._measurer = measurer

    def split(
        self,
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
        node: UASTNode | None = None,
    ) -> tuple[SourceSpan, ...]:
        """Split a source span into strictly size-bounded pieces."""

        self._validate_range(
            source_bytes,
            start_byte=start_byte,
            end_byte=end_byte,
        )

        if start_byte == end_byte:
            return ()

        spans: list[SourceSpan] = []
        cursor = start_byte

        while cursor < end_byte:
            remaining_size = self._measure_range(
                source_bytes,
                start_byte=cursor,
                end_byte=end_byte,
            )

            if remaining_size <= self._max_size:
                boundary = end_byte
            else:
                maximum_end = self._find_maximum_end(
                    source_bytes,
                    start_byte=cursor,
                    end_byte=end_byte,
                )

                boundary = self._find_preferred_boundary(
                    source_bytes,
                    start_byte=cursor,
                    maximum_end=maximum_end,
                )

                boundary = self._snap_to_utf8_boundary(
                    source_bytes,
                    start_byte=cursor,
                    boundary=boundary,
                    end_byte=end_byte,
                )

                if boundary <= cursor:
                    # This can occur only when max_size is smaller than one
                    # complete UTF-8 code point. Raw byte progress is safer
                    # than an infinite loop.
                    boundary = maximum_end

            if boundary <= cursor:
                raise RuntimeError(
                    f"Fallback splitter failed to make progress at byte {cursor}.",
                )

            spans.append(
                SourceSpan(
                    start_byte=cursor,
                    end_byte=boundary,
                    node=node,
                ),
            )

            cursor = boundary

        return tuple(spans)

    def _find_maximum_end(
        self,
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
    ) -> int:
        """Find the farthest end whose measured size is within the limit."""

        if self._measurer.unit == ChunkSizeUnit.BYTE:
            return min(
                start_byte + self._max_size,
                end_byte,
            )

        low = start_byte + 1
        high = end_byte
        best = start_byte

        while low <= high:
            middle = (low + high) // 2

            measured_size = self._measure_range(
                source_bytes,
                start_byte=start_byte,
                end_byte=middle,
            )

            if measured_size <= self._max_size:
                best = middle
                low = middle + 1
            else:
                high = middle - 1

        if best <= start_byte:
            return min(
                start_byte + 1,
                end_byte,
            )

        return best

    @staticmethod
    def _find_preferred_boundary(
        source_bytes: bytes,
        *,
        start_byte: int,
        maximum_end: int,
    ) -> int:
        """Prefer a line or whitespace boundary before the hard limit."""

        newline_index = source_bytes.rfind(
            b"\n",
            start_byte,
            maximum_end,
        )

        if newline_index >= start_byte:
            return newline_index + 1

        for index in range(
            maximum_end - 1,
            start_byte,
            -1,
        ):
            if source_bytes[index] in {
                9,  # tab
                13,  # carriage return
                32,  # space
            }:
                return index + 1

        return maximum_end

    @staticmethod
    def _snap_to_utf8_boundary(
        source_bytes: bytes,
        *,
        start_byte: int,
        boundary: int,
        end_byte: int,
    ) -> int:
        """Avoid splitting immediately before a UTF-8 continuation byte."""

        snapped_boundary = boundary

        while (
            snapped_boundary > start_byte
            and snapped_boundary < end_byte
            and (source_bytes[snapped_boundary] & 0b1100_0000) == 0b1000_0000
        ):
            snapped_boundary -= 1

        return snapped_boundary

    def _measure_range(
        self,
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
    ) -> int:
        """Measure one byte slice with the configured strategy."""

        return self._measurer.measure(
            source_bytes[start_byte:end_byte],
        )

    @staticmethod
    def _validate_range(
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
    ) -> None:
        """Validate an input range."""

        if start_byte < 0 or end_byte < start_byte or end_byte > len(source_bytes):
            raise ValueError(
                f"Invalid fallback source range: {start_byte}-{end_byte}",
            )
