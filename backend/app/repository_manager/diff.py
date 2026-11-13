"""NUL-safe representation and parser for commit-to-commit Git changes."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitChangeManifest:
    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]
    renamed: tuple[tuple[str, str], ...]
    type_changed: tuple[str, ...]

    @property
    def changed_paths(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(self.added)
                | set(self.modified)
                | set(self.type_changed)
                | {new for _, new in self.renamed}
            )
        )

    @property
    def deleted_paths(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.deleted) | {old for old, _ in self.renamed}))


def select_indexing_mode(
    *,
    base_commit_sha: str | None,
    checkpoint_compatible: bool,
    checkpoint_consistent: bool = True,
    manifest: GitChangeManifest | None,
    diff_error: str | None = None,
    force_full: bool = False,
) -> tuple[str, str | None]:
    """Select the pipeline mode from checkpoint validity and the actual diff."""
    if force_full:
        return "FULL", "Explicit full reindex requested"
    if not base_commit_sha:
        return "FULL", "No successful checkpoint exists"
    if not checkpoint_compatible:
        return "FULL_FALLBACK", "Indexing version is missing or incompatible"
    if not checkpoint_consistent:
        return "FULL_FALLBACK", "Previous indexing run left stores unsynchronized"
    if diff_error is not None:
        return "FULL_FALLBACK", diff_error
    if manifest is None:
        return "FULL_FALLBACK", "Git change manifest is unavailable"
    if not (manifest.changed_paths or manifest.deleted_paths):
        return "NOOP", None
    return "INCREMENTAL", None


def parse_name_status_z(output: str) -> GitChangeManifest:
    """Parse `git diff --name-status -z` output without splitting paths on spaces."""
    fields = output.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    renamed: list[tuple[str, str]] = []
    type_changed: list[str] = []
    cursor = 0
    while cursor < len(fields):
        status = fields[cursor]
        cursor += 1
        if status.startswith(("R", "C")):
            if cursor + 1 >= len(fields):
                raise ValueError("Malformed rename/copy record in Git diff output")
            old_path, new_path = fields[cursor : cursor + 2]
            cursor += 2
            if status.startswith("R"):
                renamed.append((old_path, new_path))
            else:
                added.append(new_path)
            continue
        if cursor >= len(fields):
            raise ValueError("Malformed path record in Git diff output")
        path = fields[cursor]
        cursor += 1
        if status == "A":
            added.append(path)
        elif status == "M":
            modified.append(path)
        elif status == "D":
            deleted.append(path)
        elif status == "T":
            type_changed.append(path)
        else:
            raise ValueError(f"Unsupported Git diff status: {status}")
    return GitChangeManifest(
        added=tuple(sorted(added)),
        modified=tuple(sorted(modified)),
        deleted=tuple(sorted(deleted)),
        renamed=tuple(sorted(renamed)),
        type_changed=tuple(sorted(type_changed)),
    )
