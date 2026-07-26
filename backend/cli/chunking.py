"""Thin CLI adapter for production source-code chunking."""

from pathlib import Path

import typer

from app.chunking import (
    ChunkCoverageError,
    ChunkingOptions,
    ChunkingResult,
    ChunkingService,
    ChunkSizeUnit,
    SourceChunk,
)
from app.parser import (
    ParserService,
    UnsupportedLanguageError,
)


cli = typer.Typer()


@cli.command(
    name="chunkv2",
    help="Parse and structurally chunk supported source-code files.",
)
def chunking_v2(
    p: str = typer.Argument(
        help="Path to a supported source file or directory.",
    ),
    unit: str = typer.Option(
        "byte",
        "--unit",
        "-u",
        help="Chunk size unit: byte or word.",
    ),
    max_chunk_size: int = typer.Option(
        500,
        "--max-size",
        "-m",
        help="Maximum size per chunk in the selected unit.",
    ),
    no_merge: bool = typer.Option(
        False,
        "--no-merge",
        help="Disable merging adjacent structural spans.",
    ),
    show_text: bool = typer.Option(
        False,
        "--show-text",
        help="Print the source content of every generated chunk.",
    ),
    verify: bool = typer.Option(
        False,
        "--verify",
        help="Fail when generated chunks violate coverage invariants.",
    ),
) -> None:
    """Parse and chunk one file or all supported files in a directory."""

    root = Path(p)

    if not root.exists():
        raise typer.BadParameter(
            f"Path does not exist: {p}",
        )

    if max_chunk_size <= 0:
        raise typer.BadParameter(
            "max-size must be greater than zero.",
        )

    size_unit = _resolve_size_unit(
        unit,
    )

    options = ChunkingOptions(
        max_size=max_chunk_size,
        size_unit=size_unit,
        merge_adjacent=not no_merge,
        verify_coverage=verify,
    )

    parser_service = ParserService()
    chunking_service = ChunkingService()

    processed_count = 0
    skipped_count = 0

    for source_path in _collect_source_paths(
        root,
    ):
        parser_file_path = _make_parser_file_path(
            root,
            source_path,
        )

        try:
            source_bytes = source_path.read_bytes()

            parse_result = parser_service.parse_bytes(
                source_bytes,
                file_path=parser_file_path,
            )
        except UnsupportedLanguageError:
            skipped_count += 1
            continue
        except OSError as exc:
            typer.echo(
                f"FAILED    : could not read {source_path}: {exc}",
                err=True,
            )
            raise typer.Exit(
                code=1,
            ) from exc

        try:
            chunking_result = chunking_service.chunk_parse_result(
                parse_result,
                options=options,
            )
        except ChunkCoverageError as exc:
            _render_coverage_failure(
                parser_file_path,
                exc,
            )
            raise typer.Exit(
                code=1,
            ) from exc

        _render_result(
            chunking_result,
            parse_status=_string_value(
                parse_result.status,
            ),
            show_text=show_text,
            verify=verify,
        )

        processed_count += 1

    if processed_count == 0:
        if root.is_file():
            raise typer.BadParameter(
                f"Unsupported source file: {root}",
            )

        typer.echo(
            "No supported source files found.",
        )

    if root.is_dir():
        typer.echo(
            f"summary   : processed={processed_count}, skipped={skipped_count}",
        )


def _collect_source_paths(
    root: Path,
) -> tuple[Path, ...]:
    """Collect deterministic file paths for CLI processing."""

    if root.is_file():
        return (root,)

    return tuple(
        sorted(
            (child for child in root.rglob("*") if child.is_file()),
            key=lambda child: child.as_posix(),
        ),
    )


def _make_parser_file_path(
    root: Path,
    source_path: Path,
) -> str:
    """Create a normalized path for ParserService output."""

    if root.is_dir():
        return source_path.relative_to(
            root,
        ).as_posix()

    return source_path.name


def _resolve_size_unit(
    unit: str,
) -> ChunkSizeUnit:
    """Convert a CLI size-unit value into the domain enum."""

    normalized_unit = unit.strip().lower()

    try:
        return ChunkSizeUnit(
            normalized_unit,
        )
    except ValueError as exc:
        supported_units = ", ".join(size_unit.value for size_unit in ChunkSizeUnit)

        raise typer.BadParameter(
            f"Unknown unit {unit!r}; expected one of: {supported_units}.",
        ) from exc


def _render_result(
    result: ChunkingResult,
    *,
    parse_status: str,
    show_text: bool,
    verify: bool,
) -> None:
    """Render one production ChunkingResult."""

    sizes = [chunk.size for chunk in result.chunks]

    typer.echo(
        "=" * 100,
    )
    typer.echo(
        "file      : "
        f"{result.file_path} "
        f"(language={result.language}, "
        f"parser={result.parser_name}, "
        f"status={parse_status})",
    )
    typer.echo(
        "config    : "
        f"unit={result.options.size_unit.value}, "
        f"max_chunk_size={result.options.max_size}, "
        f"merge_adjacent={result.options.merge_adjacent}",
    )
    typer.echo(
        f"chunks    : {result.chunk_count}",
    )
    typer.echo(
        "coverage  : "
        f"file={result.coverage.total_bytes} bytes, "
        f"covered={result.coverage.covered_bytes}, "
        f"missing={result.coverage.missing_bytes}, "
        f"overlap={result.coverage.overlap_bytes}",
    )

    if sizes:
        typer.echo(
            "chunk size: "
            f"min={min(sizes)}, "
            f"max={max(sizes)}, "
            f"over_limit={result.over_limit_count} "
            f"(unit={result.options.size_unit.value})",
        )

    if verify:
        typer.echo(
            "verify    : OK, chunks cover the file exactly",
        )

    if show_text:
        for chunk in result.chunks:
            _render_chunk(
                chunk,
            )

    typer.echo(
        "=" * 100,
    )


def _render_chunk(
    chunk: SourceChunk,
) -> None:
    """Render one chunk and its normalized metadata."""

    symbol = _format_symbol(
        chunk,
    )

    typer.echo(
        "-" * 50,
    )
    typer.echo(
        f"chunk #{chunk.index} "
        f"(size={chunk.size}, "
        f"bytes={chunk.start_byte}-{chunk.end_byte}, "
        f"symbol={symbol})",
    )
    typer.echo(
        chunk.content,
    )


def _format_symbol(
    chunk: SourceChunk,
) -> str:
    """Format optional chunk symbol metadata."""

    if chunk.symbol_name is None:
        return "-"

    if chunk.symbol_kind is None:
        return chunk.symbol_name

    return f"{chunk.symbol_kind}:{chunk.symbol_name}"


def _render_coverage_failure(
    file_path: str,
    error: ChunkCoverageError,
) -> None:
    """Render coverage issues before exiting with failure."""

    typer.echo(
        "=" * 100,
        err=True,
    )
    typer.echo(
        f"file      : {file_path}",
        err=True,
    )

    for issue in error.coverage.issues:
        typer.echo(
            f"FAILED    : {issue}",
            err=True,
        )

    typer.echo(
        "=" * 100,
        err=True,
    )


def _string_value(
    value: object,
) -> str:
    """Return an enum value or the object's string representation."""

    raw_value = getattr(
        value,
        "value",
        value,
    )

    return str(
        raw_value,
    )
