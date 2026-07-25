from typing import Any

import typer
from app.parser.languages import get_language_registry
from app.parser.uast import UASTNode, TypeDefinitionNode, FunctionNode, VariableNode
from abc import ABC, abstractmethod

from pathlib import Path
from dataclasses import dataclass, field
from app.parser import UnsupportedLanguageError

cli = typer.Typer()


@dataclass
class ChunkData:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    size: int = field(default=0)
    """To reduce re calculation size only, won't be a part of embedding input"""

    start_byte: int = field(default=0)
    """Start byte index(in file) of ``text``. Start from 0."""
    end_byte: int = field(default=0)
    """End byte index(in file) of ``text``. Start from 0."""

    def __str__(self) -> str:
        header_lines = []
        for key, value in self.metadata.items():
            header_lines.append(f"# {key}: {value}")
        if len(header_lines) == 0:
            return self.text
        header = "\n".join(header_lines)
        return f"{header}\n{self.text}"


class CodeChunker(ABC):
    @abstractmethod
    def calc_chunk_size(self, text: str | bytes) -> int:
        """
        Calculate chunk size for given text.
        The unit of measurement depend on how this method works.
        Args:
            text: text to calculate chunk size.

        Returns:
            Chunk size as an integer. The unit of measurement depend on how this method works.
        """
        pass

    @staticmethod
    def get_text(source_bytes: bytes, start_byte: int, end_byte: int) -> str:
        return source_bytes[start_byte:end_byte].decode("utf-8", errors="replace")

    def make_chunk(
        self, source_bytes: bytes, start_byte: int, end_byte: int
    ) -> ChunkData:
        text = self.get_text(source_bytes, start_byte, end_byte)
        return ChunkData(
            text=text,
            metadata={},
            size=self.calc_chunk_size(text),
            start_byte=start_byte,
            end_byte=end_byte,
        )

    def merge_chunks(self, chunks: list[ChunkData], source_bytes: bytes) -> ChunkData:
        """
        Merge contiguous chunks by re-slicing the source between the first and the last one.
        Slicing(instead of joining texts) keeps whatever bytes sit between them, so merging
        can never lose source.
        """
        return self.make_chunk(source_bytes, chunks[0].start_byte, chunks[-1].end_byte)

    def __init__(
        self,
        max_chunk_size: int,
        auto_merge_chunk: bool = True,
    ) -> None:
        """

        Args:
            max_chunk_size: maximum chunk size for each chunk. The unit of measurement depend on how method
                ``calc_chunk_size`` was implemented.
            auto_merge_chunk: merge chunk until hit chunk size limit
        """
        self.max_chunk_size = max_chunk_size
        self.auto_merge_chunk = auto_merge_chunk

    @staticmethod
    def snap_to_line_start(source_bytes: bytes, offset: int, floor: int) -> int:
        """
        Move ``offset`` back to the start of its line when everything before it on that line
        is indentation. A definition's span starts at its keyword(``def``/``class``), not at
        the start of the line, so without this the indentation of the first line is swallowed
        by the previous chunk and the chunk comes out mis-indented.

        Args:
            source_bytes: source code as bytes.
            offset: byte offset to snap.
            floor: lowest offset allowed, never move past it.

        Returns:
            Snapped offset, or the original one when the line holds more than indentation.
        """
        i = offset
        while i > floor and source_bytes[i - 1 : i] in (b" ", b"\t"):
            i -= 1
        if i == floor or source_bytes[i - 1 : i] == b"\n":
            return i
        return offset

    def split_span(
        self,
        node: UASTNode,
        file_bytes: bytes,
        start_byte: int,
        end_byte: int,
    ) -> list[tuple[int, int, UASTNode | None]]:
        """
        Split ``[start_byte, end_byte)`` into units that cover it exactly - no byte lost,
        no byte duplicated.

        Children of a node do not cover their parent's span: decorators, comments, blank lines,
        the ``class X:`` line itself and wrappers the UAST flattens away(eg. ``if TYPE_CHECKING:``)
        all sit between them. Those in-between bytes are attached to the unit that follows them,
        because every one of them reads as a prefix of the construct coming next.

        Args:
            node: parent node whose children are the split points.
            file_bytes: source code as bytes.
            start_byte: start of the span to cover.
            end_byte: end of the span to cover.

        Returns:
            List of ``(start, end, child)`` covering the span. ``child`` is ``None`` for a unit
            that holds only text no child claimed.
        """
        # Partition into child pieces and gap pieces.
        pieces: list[tuple[int, int, UASTNode | None]] = []
        cursor = start_byte
        for child in node.children:
            child_start = self.snap_to_line_start(file_bytes, child.start_byte, cursor)
            child_end = child.end_byte
            if child_start < cursor or child_end > end_byte or child_end <= child_start:
                # Overlapping, escaping or empty child: skipping it keeps the invariant,
                # its bytes simply stay inside the preceding unit.
                continue
            if child_start > cursor:
                pieces.append((cursor, child_start, None))
            pieces.append((child_start, child_end, child))
            cursor = child_end
        if cursor < end_byte:
            pieces.append((cursor, end_byte, None))

        # Attach each gap to the child that follows it.
        units: list[tuple[int, int, UASTNode | None]] = []
        pending: tuple[int, int] | None = None
        for piece_start, piece_end, child in pieces:
            if child is None:
                pending = (
                    pending[0] if pending is not None else piece_start,
                    piece_end,
                )
                continue
            if pending is not None:
                gap_size = self.calc_chunk_size(self.get_text(file_bytes, *pending))
                if gap_size > self.max_chunk_size:
                    # Too big to lead-attach: welding a whole module-level script onto the
                    # next definition would drown it. Keep it on its own.
                    units.append((pending[0], pending[1], None))
                else:
                    piece_start = pending[0]
                pending = None
            units.append((piece_start, piece_end, child))

        if pending is not None:
            # Trailing gap: no child follows it.
            if len(units) != 0 and file_bytes[pending[0] : pending[1]].strip() == b"":
                last_start, _, last_child = units[-1]
                units[-1] = (last_start, pending[1], last_child)
            else:
                units.append((pending[0], pending[1], None))
        return units

    def chunk(
        self,
        node: UASTNode,
        file_bytes: bytes,
        start_byte: int | None = None,
        end_byte: int | None = None,
    ) -> list[ChunkData]:
        """
        Chunk ``node``. The returned chunks cover the whole span exactly.

        Args:
            node: node to chunk.
            file_bytes: source code as bytes.
            start_byte: span start, defaults to the node's own start. Pass it to keep text that
                was attached in front of the node(eg. its decorators).
            end_byte: span end, defaults to the node's own end. Must be passed together with
                ``start_byte``: a trailing gap can push a unit's end past the node's own end.
        """
        start = node.start_byte if start_byte is None else start_byte
        end = node.end_byte if end_byte is None else end_byte

        chunks: list[ChunkData] = []

        span_size = self.calc_chunk_size(self.get_text(file_bytes, start, end))
        if span_size <= self.max_chunk_size:
            chunks.append(self.make_chunk(file_bytes, start, end))
        else:
            units = self.split_span(node, file_bytes, start, end)
            if not self.auto_merge_chunk:
                # auto merge chunk: False
                for unit_start, unit_end, child in units:
                    if child is None:
                        chunks.append(self.make_chunk(file_bytes, unit_start, unit_end))
                    else:
                        chunks += self.chunk(child, file_bytes, unit_start, unit_end)
            else:
                # auto merge chunk: true
                stack: list[ChunkData] = []
                for unit_start, unit_end, child in units:
                    if child is None:
                        child_chunks = [
                            self.make_chunk(file_bytes, unit_start, unit_end)
                        ]
                    else:
                        child_chunks = self.chunk(
                            child, file_bytes, unit_start, unit_end
                        )

                    if len(child_chunks) == 1:
                        child_chunk = child_chunks[0]
                        total_size = sum([_.size for _ in stack]) + child_chunk.size

                        if total_size > self.max_chunk_size and len(stack) != 0:
                            merged_chunk = self.merge_chunks(stack, file_bytes)
                            chunks.append(merged_chunk)
                            stack.clear()

                        stack.append(child_chunk)
                    else:
                        if len(stack) != 0:
                            merged_chunk = self.merge_chunks(stack, file_bytes)
                            chunks.append(merged_chunk)
                            stack.clear()
                        chunks += child_chunks

                # Whatever is left in the stack when the loop ends still has to be
                # emitted, otherwise the last children are dropped.
                if len(stack) != 0:
                    merged_chunk = self.merge_chunks(stack, file_bytes)
                    chunks.append(merged_chunk)
                    stack.clear()

        if len(chunks) == 0:
            # Node is over the limit but has no child to split on(eg. a function whose
            # body holds no captured node). Emit it whole instead of dropping the text:
            # an over-sized chunk is visible downstream, a missing one is not.
            chunks.append(self.make_chunk(file_bytes, start, end))
        return chunks


class ByteChunker(CodeChunker):
    """``calc_chunk_size`` counts UTF-8 bytes."""

    def calc_chunk_size(self, text: str | bytes) -> int:
        if isinstance(text, str):
            return len(text.encode("utf-8"))
        return len(text)


class WordChunker(CodeChunker):
    """``calc_chunk_size`` counts whitespace-separated words."""

    def calc_chunk_size(self, text: str | bytes) -> int:
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        return len(text.split())


CHUNKER_UNITS: dict[str, type[CodeChunker]] = {
    "byte": ByteChunker,
    "word": WordChunker,
}


def verify_coverage(chunks: list[ChunkData], file_bytes: bytes) -> list[str]:
    """
    Check that ``chunks`` cover ``file_bytes`` exactly: no byte lost, no byte duplicated.

    Compares bytes rather than text length, because decoding with ``errors="replace"``
    changes the character count.

    Args:
        chunks: chunks to check, in order.
        file_bytes: source code as bytes.

    Returns:
        List of problems found. Empty when the coverage is exact.
    """
    problems: list[str] = []
    if len(chunks) == 0:
        if len(file_bytes) != 0:
            problems.append(f"no chunk emitted for a {len(file_bytes)} bytes file")
        return problems

    if chunks[0].start_byte != 0:
        problems.append(f"first chunk starts at {chunks[0].start_byte}, expected 0")
    if chunks[-1].end_byte != len(file_bytes):
        problems.append(
            f"last chunk ends at {chunks[-1].end_byte}, expected {len(file_bytes)}"
        )
    for previous, current in zip(chunks, chunks[1:]):
        if previous.end_byte != current.start_byte:
            kind = "gap" if previous.end_byte < current.start_byte else "overlap"
            problems.append(
                f"{kind} between byte {previous.end_byte} and {current.start_byte}"
            )

    rebuilt = b"".join(
        file_bytes[chunk.start_byte : chunk.end_byte] for chunk in chunks
    )
    if rebuilt != file_bytes:
        problems.append("concatenating the chunks does not rebuild the file")
    return problems


type ChunkLevel = dict[type[UASTNode], ChunkLevel]


def chunk_file(node: UASTNode, file_bytes: bytes, chunk_level: ChunkLevel) -> list[str]:
    chunks = []

    allowed_types = chunk_level.keys()
    for child in node.children:
        for allowed_type in allowed_types:
            if isinstance(child, allowed_type):
                sub_level = chunk_level[allowed_type]
                chunks += chunk_file(child, file_bytes, sub_level)
                break

    if len(chunks) == 0:
        text = file_bytes[node.start_byte : node.end_byte].decode("utf-8")
        chunks.append(text)
    return chunks


@cli.command(name="chunk", help="Test Chunking, currently support only python")
def chunking(
    p: str = typer.Argument(help="Path to the file or directory"),
    output_path: str | None = typer.Option(None, "--out-file"),
) -> None:
    import gc

    gc.disable()

    root = Path(p)
    if not root.exists():
        raise ValueError("Path does not exist")

    paths: list[Path] = []
    if root.is_file():
        paths.append(root)
    else:
        for child in root.rglob("*"):
            if child.is_file():
                paths.append(child)
    warnings = []
    result: dict[str, list[str]] = {}

    # chunk files
    lang_registry = get_language_registry()

    level: ChunkLevel = {
        TypeDefinitionNode: {
            TypeDefinitionNode: {},  # class in class
            FunctionNode: {},  # method in class
            VariableNode: {},  # field/constant in class
        },
        FunctionNode: {},
        VariableNode: {},
    }
    for path in paths:
        parser = lang_registry.get_parser("python")
        converter = lang_registry.get_converter("python")
        try:
            if lang_registry.resolve_language_name(path.name) != "python":
                warnings.append(f"Ignoring file {path} because it is not python")
                continue
        except UnsupportedLanguageError:
            continue

        file_bytes = path.read_bytes()

        parser = lang_registry.get_parser("python")
        converter = lang_registry.get_converter("python")
        ts_tree = parser.parse(file_bytes)
        uast_root = converter.convert(ts_tree, source_bytes=file_bytes)

        result[str(path.absolute())] = chunk_file(uast_root, file_bytes, level)
    gc.enable()

    if output_path is None:
        for file_name, chunks in result.items():
            print(
                "=" * 100,
                f"file: {file_name} separate into {len(chunks)} chunks:",
                sep="\n",
            )
            for chunk in chunks:
                print(chunk)
                print("-" * 50)
            print("=" * 100)
    else:
        output = Path(output_path)
        if not (output.exists()) or not (output.is_file()):
            raise ValueError("Output path does not exist")
        pass


@cli.command(
    name="chunkv2", help="Test CodeChunker. Size unit is selectable(byte or word)."
)
def chunking_v2(
    p: str = typer.Argument(help="Path to the file or directory"),
    unit: str = typer.Option("byte", "--unit", "-u", help="Size unit: byte or word"),
    max_chunk_size: int = typer.Option(
        500, "--max-size", "-m", help="Max size per chunk, in the selected unit"
    ),
    no_merge: bool = typer.Option(
        False, "--no-merge", help="Disable auto merging of small sibling chunks"
    ),
    show_text: bool = typer.Option(
        False, "--show-text", help="Print chunk content, not only the summary"
    ),
    verify: bool = typer.Option(
        False, "--verify", help="Fail when the chunks do not cover the file exactly"
    ),
) -> None:
    if unit not in CHUNKER_UNITS:
        raise typer.BadParameter(
            f"Unknown unit {unit!r}, expected one of: {', '.join(CHUNKER_UNITS)}"
        )

    root = Path(p)
    if not root.exists():
        raise typer.BadParameter(f"Path does not exist: {p}")

    paths: list[Path] = []
    if root.is_file():
        paths.append(root)
    else:
        paths = sorted(child for child in root.rglob("*") if child.is_file())

    chunker = CHUNKER_UNITS[unit](
        max_chunk_size=max_chunk_size,
        auto_merge_chunk=not no_merge,
    )
    lang_registry = get_language_registry()

    for path in paths:
        try:
            lang_name = lang_registry.resolve_language_name(path.name)
        except UnsupportedLanguageError:
            continue

        file_bytes = path.read_bytes()
        ts_tree = lang_registry.get_parser(lang_name).parse(file_bytes)
        uast_root = lang_registry.get_converter(lang_name).convert(
            ts_tree, source_bytes=file_bytes
        )

        # Clamp to the whole file so coverage never depends on the root node's own span.
        chunks = chunker.chunk(uast_root, file_bytes, 0, len(file_bytes))

        covered = sum(chunk.end_byte - chunk.start_byte for chunk in chunks)
        missing = len(file_bytes) - covered
        sizes = [chunk.size for chunk in chunks]

        print("=" * 100)
        print(f"file      : {path} ({lang_name})")
        print(
            f"config    : unit={unit}, max_chunk_size={max_chunk_size}, auto_merge={not no_merge}"
        )
        print(f"chunks    : {len(chunks)}")
        print(
            f"coverage  : file={len(file_bytes)} bytes, covered={covered}, missing={missing}"
        )
        if sizes:
            over_limit = sum(1 for size in sizes if size > max_chunk_size)
            print(
                f"chunk size: min={min(sizes)}, max={max(sizes)}, over_limit={over_limit} (unit={unit})"
            )

        if verify:
            problems = verify_coverage(chunks, file_bytes)
            if len(problems) != 0:
                for problem in problems:
                    print(f"FAILED    : {problem}")
                raise typer.Exit(code=1)
            print("verify    : OK, chunks cover the file exactly")

        if show_text:
            for index, chunk in enumerate(chunks):
                print(
                    "-" * 50,
                    f"chunk #{index} (size={chunk.size}, bytes={chunk.start_byte}-{chunk.end_byte})",
                    sep="\n",
                )
                print(str(chunk))
        print("=" * 100)
