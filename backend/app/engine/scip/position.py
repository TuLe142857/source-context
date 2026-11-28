"""Convert SCIP source positions into byte offsets.

SCIP addresses source code as ``(line, character)`` pairs while the UAST carries
``start_byte``/``end_byte`` produced by Tree-sitter. The two only agree on pure ASCII:
SCIP counts *characters* from the start of a line whereas Tree-sitter counts *bytes*.

Every conversion between the two coordinate systems goes through this module, so the
encoding difference — and any future ``Document.position_encoding`` variation between
indexers — is handled in exactly one place.
"""

from collections.abc import Sequence

_LINE_FEED = 0x0A


def build_line_index(source: bytes) -> list[int]:
    """Return the byte offset at which each line of ``source`` starts.

    The result always contains at least one entry (``0``) so an empty file still has
    one line.

    Args:
        source: Raw file content.

    Returns:
        Byte offsets of every line start, in ascending order.
    """

    line_starts = [0]
    offset = source.find(_LINE_FEED)
    while offset != -1:
        line_starts.append(offset + 1)
        offset = source.find(_LINE_FEED, offset + 1)
    return line_starts


class LineIndex:
    """Byte-offset lookup for one source file.

    Holds the file content next to its line table because every conversion needs both:
    the line table locates the line, the content is required to measure how many bytes
    the leading ``character`` code points actually occupy.
    """

    __slots__ = ("_line_starts", "_source")

    def __init__(self, source: bytes) -> None:
        self._source = source
        self._line_starts = build_line_index(source)

    @property
    def line_count(self) -> int:
        """Number of lines in the file."""

        return len(self._line_starts)

    def to_byte_offset(self, line: int, character: int) -> int:
        """Convert a SCIP ``(line, character)`` position into a byte offset.

        Positions past the end of the file or past the end of a line are clamped
        instead of raising: a stale index legitimately points outside the current
        file, and the caller detects that through the identifier check rather than
        through an exception.

        Args:
            line: Zero-based line number.
            character: Zero-based character offset from the start of that line.

        Returns:
            Byte offset from the start of the file.

        Raises:
            ValueError: If ``line`` or ``character`` is negative.
        """

        if line < 0 or character < 0:
            raise ValueError(
                f"position must be non-negative, got line={line}, character={character}"
            )

        if line >= len(self._line_starts):
            return len(self._source)

        line_start = self._line_starts[line]
        line_end = (
            self._line_starts[line + 1]
            if line + 1 < len(self._line_starts)
            else len(self._source)
        )

        # Decoding the line and re-encoding its prefix is what cancels out the
        # character-vs-byte difference for multi-byte UTF-8.
        text = self._source[line_start:line_end].decode("utf-8", errors="replace")
        if character >= len(text):
            return line_end

        return line_start + len(text[:character].encode("utf-8"))

    def range_to_bytes(self, scip_range: Sequence[int]) -> tuple[int, int]:
        """Convert an ``Occurrence.range`` into a ``(start_byte, end_byte)`` span.

        SCIP encodes a range either as ``[line, start_character, end_character]`` when
        it fits on a single line, or as ``[start_line, start_character, end_line,
        end_character]`` when it spans several.

        Args:
            scip_range: The raw ``range`` field of an occurrence.

        Returns:
            Half-open byte span ``[start_byte, end_byte)``.

        Raises:
            ValueError: If the range is neither three nor four elements long.
        """

        if len(scip_range) == 3:
            line, start_character, end_character = scip_range
            return (
                self.to_byte_offset(line, start_character),
                self.to_byte_offset(line, end_character),
            )

        if len(scip_range) == 4:
            start_line, start_character, end_line, end_character = scip_range
            return (
                self.to_byte_offset(start_line, start_character),
                self.to_byte_offset(end_line, end_character),
            )

        raise ValueError(
            f"SCIP range must have 3 or 4 elements, got {len(scip_range)}: {list(scip_range)}"
        )

    def slice_text(self, start_byte: int, end_byte: int) -> str:
        """Return the source text of a byte span, for identifier comparison."""

        return self._source[start_byte:end_byte].decode("utf-8", errors="replace")
