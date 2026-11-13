import pytest

from app.repository_manager.diff import parse_name_status_z, select_indexing_mode


def test_parse_name_status_handles_spaces_and_renames() -> None:
    manifest = parse_name_status_z(
        "A\0new file.py\0M\0dir/changed file.py\0D\0old.py\0R100\0before.py\0after.py\0T\0link"
    )

    assert manifest.added == ("new file.py",)
    assert manifest.modified == ("dir/changed file.py",)
    assert manifest.deleted_paths == ("before.py", "old.py")
    assert manifest.renamed == (("before.py", "after.py"),)
    assert manifest.type_changed == ("link",)


@pytest.mark.parametrize("output", ["A", "R100\0old", "X\0file"])
def test_parse_name_status_rejects_malformed_output(output: str) -> None:
    with pytest.raises(ValueError):
        parse_name_status_z(output)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"base_commit_sha": None, "checkpoint_compatible": False, "manifest": None},
            ("FULL", "No successful checkpoint exists"),
        ),
        (
            {
                "base_commit_sha": "base",
                "checkpoint_compatible": True,
                "manifest": parse_name_status_z(""),
            },
            ("NOOP", None),
        ),
        (
            {
                "base_commit_sha": "base",
                "checkpoint_compatible": True,
                "manifest": parse_name_status_z("M\0src/a.py\0"),
            },
            ("INCREMENTAL", None),
        ),
        (
            {
                "base_commit_sha": "base",
                "checkpoint_compatible": False,
                "manifest": None,
            },
            ("FULL_FALLBACK", "Indexing version is missing or incompatible"),
        ),
        (
            {
                "base_commit_sha": "missing-object",
                "checkpoint_compatible": True,
                "manifest": None,
                "diff_error": "base commit unavailable",
            },
            ("FULL_FALLBACK", "base commit unavailable"),
        ),
        (
            {
                "base_commit_sha": "base",
                "checkpoint_compatible": True,
                "checkpoint_consistent": False,
                "manifest": parse_name_status_z(""),
            },
            ("FULL_FALLBACK", "Previous indexing run left stores unsynchronized"),
        ),
        (
            {
                "base_commit_sha": "base",
                "checkpoint_compatible": True,
                "manifest": parse_name_status_z("M\0src/a.py\0"),
                "force_full": True,
            },
            ("FULL", "Explicit full reindex requested"),
        ),
    ],
)
def test_select_indexing_mode(
    kwargs: dict[str, object], expected: tuple[str, str | None]
) -> None:
    assert select_indexing_mode(**kwargs) == expected
