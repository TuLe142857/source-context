"""Integration tests for the production chunking CLI adapter."""

from pathlib import Path

from typer.testing import CliRunner

from cli import cli


runner = CliRunner()


def test_chunkv2_is_registered_and_legacy_chunk_is_removed() -> None:
    help_result = runner.invoke(
        cli,
        [
            "--help",
        ],
    )

    assert help_result.exit_code == 0
    assert "chunkv2" in help_result.output

    legacy_result = runner.invoke(
        cli,
        [
            "chunk",
            "--help",
        ],
    )

    assert legacy_result.exit_code != 0


def test_chunkv2_chunks_python_with_exact_coverage(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "service.py"
    source_path.write_text(
        ('def create_user(name: str) -> dict[str, str]:\n    return {"name": name}\n'),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "chunkv2",
            str(source_path),
            "--max-size",
            "32",
            "--verify",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "language=python" in result.output
    assert "parser=python" in result.output
    assert "missing=0" in result.output
    assert "overlap=0" in result.output
    assert "over_limit=0" in result.output
    assert "verify    : OK, chunks cover the file exactly" in result.output


def test_chunkv2_uses_tsx_parser_dialect(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "Card.tsx"
    source_path.write_text(
        (
            "type Props = {\n"
            "  title: string;\n"
            "};\n"
            "\n"
            "export const Card = "
            "({ title }: Props): JSX.Element => (\n"
            "  <article>{title}</article>\n"
            ");\n"
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "chunkv2",
            str(source_path),
            "--max-size",
            "48",
            "--verify",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "language=typescript" in result.output
    assert "parser=tsx" in result.output
    assert "missing=0" in result.output
    assert "overlap=0" in result.output


def test_chunkv2_show_text_outputs_chunk_content(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "message.js"
    source_path.write_text(
        'export const message = "hello";\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "chunkv2",
            str(source_path),
            "--max-size",
            "20",
            "--show-text",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "chunk #0" in result.output
    assert "export const" in result.output


def test_chunkv2_rejects_unknown_size_unit(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "service.py"
    source_path.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "chunkv2",
            str(source_path),
            "--unit",
            "character",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown unit" in result.output


def test_chunkv2_directory_skips_unsupported_files(
    tmp_path: Path,
) -> None:
    supported_path = tmp_path / "service.py"
    supported_path.write_text(
        "value = 1\n",
        encoding="utf-8",
    )

    unsupported_path = tmp_path / "notes.txt"
    unsupported_path.write_text(
        "not source code",
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "chunkv2",
            str(tmp_path),
            "--verify",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "processed=1" in result.output
    assert "skipped=1" in result.output
