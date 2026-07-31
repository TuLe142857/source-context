"""Production service for structural source-code chunking."""

from collections.abc import Sequence

from app.parser.contracts import ParseResult
from app.parser.uast import (
    ContainerNode,
    UASTNode,
)

from .contracts import (
    ChunkingOptions,
    ChunkingResult,
    SourceChunk,
)
from .coverage import verify_chunk_coverage
from .exceptions import ChunkCoverageError
from .fallback import FallbackSpanSplitter
from .size import (
    ChunkSizeMeasurer,
    get_size_measurer,
)
from .structural import (
    SourceSpan,
    StructuralSpanSplitter,
)


class ChunkingService:
    """Convert a parsed source file into exact structural chunks."""

    def chunk_parse_result(
        self,
        parse_result: ParseResult,
        *,
        options: ChunkingOptions | None = None,
    ) -> ChunkingResult:
        """Chunk one ParserService result."""

        resolved_options = options if options is not None else ChunkingOptions()

        root = parse_result.uast_root

        if not isinstance(
            root,
            ContainerNode,
        ):
            raise TypeError(
                "ParseResult.uast_root must be a ContainerNode",
            )

        source_bytes = root.source_bytes

        if source_bytes is None:
            raise ValueError(
                "ParseResult UAST root does not contain source_bytes",
            )

        if len(source_bytes) != parse_result.source_size_bytes:
            raise ValueError(
                "ParseResult source size does not match the UAST source bytes",
            )

        measurer = get_size_measurer(
            resolved_options.size_unit,
        )

        structural_splitter = StructuralSpanSplitter()
        fallback_splitter = FallbackSpanSplitter(
            max_size=resolved_options.max_size,
            measurer=measurer,
        )

        spans = self._split_node(
            root,
            source_bytes,
            start_byte=0,
            end_byte=len(source_bytes),
            options=resolved_options,
            measurer=measurer,
            structural_splitter=(structural_splitter),
            fallback_splitter=(fallback_splitter),
        )

        chunks = self._build_chunks(
            spans,
            source_bytes,
            file_path=parse_result.file_path,
            language=parse_result.language,
            parser_name=parse_result.parser_name,
            measurer=measurer,
        )

        coverage = verify_chunk_coverage(
            chunks,
            source_bytes,
            max_size=resolved_options.max_size,
            measurer=measurer,
        )

        if resolved_options.verify_coverage and not coverage.is_exact:
            raise ChunkCoverageError(
                coverage,
            )

        return ChunkingResult(
            file_path=parse_result.file_path,
            language=parse_result.language,
            parser_name=parse_result.parser_name,
            options=resolved_options,
            chunks=chunks,
            coverage=coverage,
        )

    def _split_node(
        self,
        node: UASTNode,
        source_bytes: bytes,
        *,
        start_byte: int,
        end_byte: int,
        options: ChunkingOptions,
        measurer: ChunkSizeMeasurer,
        structural_splitter: StructuralSpanSplitter,
        fallback_splitter: FallbackSpanSplitter,
    ) -> tuple[SourceSpan, ...]:
        """Recursively split one UAST-backed source span."""

        if start_byte == end_byte:
            return ()

        measured_size = measurer.measure(
            source_bytes[start_byte:end_byte],
        )

        if measured_size <= options.max_size:
            return (
                SourceSpan(
                    start_byte=start_byte,
                    end_byte=end_byte,
                    node=node,
                ),
            )

        structural_spans = structural_splitter.split(
            node,
            source_bytes,
            start_byte=start_byte,
            end_byte=end_byte,
        )

        has_structural_child = any(span.node is not None for span in structural_spans)

        if not has_structural_child:
            return fallback_splitter.split(
                source_bytes,
                start_byte=start_byte,
                end_byte=end_byte,
                node=node,
            )

        result: list[SourceSpan] = []

        for span in structural_spans:
            if span.node is None:
                result.extend(
                    fallback_splitter.split(
                        source_bytes,
                        start_byte=span.start_byte,
                        end_byte=span.end_byte,
                        node=None,
                    ),
                )
                continue

            result.extend(
                self._split_node(
                    span.node,
                    source_bytes,
                    start_byte=span.start_byte,
                    end_byte=span.end_byte,
                    options=options,
                    measurer=measurer,
                    structural_splitter=(structural_splitter),
                    fallback_splitter=(fallback_splitter),
                ),
            )

        if not result:
            return fallback_splitter.split(
                source_bytes,
                start_byte=start_byte,
                end_byte=end_byte,
                node=node,
            )

        if options.merge_adjacent:
            return self._merge_adjacent(
                result,
                source_bytes,
                parent_node=node,
                max_size=options.max_size,
                measurer=measurer,
            )

        return tuple(result)

    @staticmethod
    def _merge_adjacent(
        spans: Sequence[SourceSpan],
        source_bytes: bytes,
        *,
        parent_node: UASTNode,
        max_size: int,
        measurer: ChunkSizeMeasurer,
    ) -> tuple[SourceSpan, ...]:
        """Greedily merge contiguous spans under the size limit."""

        if not spans:
            return ()

        merged: list[SourceSpan] = []
        pending = spans[0]

        for current in spans[1:]:
            are_contiguous = pending.end_byte == current.start_byte

            combined_size = measurer.measure(
                source_bytes[pending.start_byte : current.end_byte],
            )

            if are_contiguous and combined_size <= max_size:
                merged_node = ChunkingService._select_merged_node(
                    pending.node,
                    current.node,
                    parent_node=parent_node,
                )
                pending = SourceSpan(
                    start_byte=(pending.start_byte),
                    end_byte=current.end_byte,
                    node=merged_node,
                )
                continue

            merged.append(
                pending,
            )
            pending = current

        merged.append(
            pending,
        )

        return tuple(merged)

    @staticmethod
    def _select_merged_node(
        left_node: UASTNode | None,
        right_node: UASTNode | None,
        *,
        parent_node: UASTNode,
    ) -> UASTNode | None:
        """Select representative symbol metadata for a merged span.

        A symbol merged only with surrounding gap text keeps its metadata.
        Spans belonging to different symbols are represented by their parent.
        """

        if left_node is None:
            return right_node

        if right_node is None:
            return left_node

        if left_node is right_node:
            return left_node

        return parent_node

    @staticmethod
    def _build_chunks(
        spans: Sequence[SourceSpan],
        source_bytes: bytes,
        *,
        file_path: str,
        language: str,
        parser_name: str,
        measurer: ChunkSizeMeasurer,
    ) -> tuple[SourceChunk, ...]:
        """Convert internal spans into public SourceChunk objects."""

        chunks: list[SourceChunk] = []

        for index, span in enumerate(
            spans,
        ):
            source_slice = source_bytes[span.start_byte : span.end_byte]

            symbol_name, symbol_kind = ChunkingService._get_symbol_metadata(
                span.node,
            )

            chunks.append(
                SourceChunk(
                    index=index,
                    file_path=file_path,
                    language=language,
                    parser_name=parser_name,
                    start_byte=span.start_byte,
                    end_byte=span.end_byte,
                    size=measurer.measure(
                        source_slice,
                    ),
                    content=source_slice.decode(
                        "utf-8",
                        errors="replace",
                    ),
                    symbol_name=symbol_name,
                    symbol_kind=symbol_kind,
                ),
            )

        return tuple(chunks)

    @staticmethod
    def _get_symbol_metadata(
        node: UASTNode | None,
    ) -> tuple[
        str | None,
        str | None,
    ]:
        """Extract normalized symbol metadata from a UAST node."""

        if node is None or isinstance(
            node,
            ContainerNode,
        ):
            return None, None

        symbol_kind_value = getattr(
            node,
            "kind",
            None,
        )

        symbol_kind = (
            symbol_kind_value
            if isinstance(
                symbol_kind_value,
                str,
            )
            else node.node_type
        )

        return (
            node.name,
            symbol_kind,
        )
