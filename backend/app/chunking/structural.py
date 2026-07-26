"""Structural source-span partitioning based on UAST children."""

from dataclasses import dataclass

from app.parser.uast import UASTNode


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """One exact non-empty byte span associated with a UAST node."""

    start_byte: int
    end_byte: int
    node: UASTNode | None = None

    def __post_init__(self) -> None:
        if self.start_byte < 0:
            raise ValueError(
                "start_byte must not be negative",
            )

        if self.end_byte <= self.start_byte:
            raise ValueError(
                "end_byte must be greater than start_byte",
            )

    @property
    def byte_size(self) -> int:
        """Return the raw byte length of the span."""

        return self.end_byte - self.start_byte


class StructuralSpanSplitter:
    """Partition a parent source span around direct UAST children."""

    def split(
        self,
        node: UASTNode,
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
    ) -> tuple[SourceSpan, ...]:
        """Return an exact partition of a parent span.

        Direct child spans are preserved as structural units. Bytes not
        claimed by a child become gap spans with ``node=None``.
        """

        self._validate_range(
            source_bytes,
            start_byte=start_byte,
            end_byte=end_byte,
        )

        if start_byte == end_byte:
            return ()

        spans: list[SourceSpan] = []
        cursor = start_byte

        ordered_children = sorted(
            node.children,
            key=lambda child: (
                child.start_byte,
                child.end_byte,
            ),
        )

        for child in ordered_children:
            original_start = child.start_byte
            child_end = child.end_byte

            if (
                original_start < cursor
                or child_end > end_byte
                or child_end <= original_start
            ):
                # Invalid or overlapping children are ignored. Their bytes
                # remain covered by the parent/gap span.
                continue

            snapped_start = self._snap_to_line_start(
                source_bytes,
                offset=original_start,
                floor=cursor,
            )

            child_start = snapped_start if snapped_start >= cursor else original_start

            if child_start < cursor:
                continue

            if child_start > cursor:
                spans.append(
                    SourceSpan(
                        start_byte=cursor,
                        end_byte=child_start,
                    ),
                )

            spans.append(
                SourceSpan(
                    start_byte=child_start,
                    end_byte=child_end,
                    node=child,
                ),
            )

            cursor = child_end

        if cursor < end_byte:
            spans.append(
                SourceSpan(
                    start_byte=cursor,
                    end_byte=end_byte,
                ),
            )

        if not spans:
            return (
                SourceSpan(
                    start_byte=start_byte,
                    end_byte=end_byte,
                ),
            )

        return tuple(spans)

    @staticmethod
    def _snap_to_line_start(
        source_bytes: bytes,
        *,
        offset: int,
        floor: int,
    ) -> int:
        """Include indentation preceding a structural child."""

        cursor = offset

        while cursor > floor and source_bytes[cursor - 1 : cursor] in {
            b" ",
            b"\t",
        }:
            cursor -= 1

        if cursor == floor:
            return cursor

        if source_bytes[cursor - 1 : cursor] in {
            b"\n",
            b"\r",
        }:
            return cursor

        return offset

    @staticmethod
    def _validate_range(
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
    ) -> None:
        """Validate a source range before partitioning."""

        if start_byte < 0 or end_byte < start_byte or end_byte > len(source_bytes):
            raise ValueError(
                f"Invalid structural source range: {start_byte}-{end_byte}",
            )
