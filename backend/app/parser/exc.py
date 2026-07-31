class UnsupportedLanguageError(Exception):
    pass


class StaleScannedSourceFileError(RuntimeError):
    """Raised when a source file changes between scanning and parsing."""

    def __init__(
        self,
        relative_path: str,
        *,
        expected_size: int,
        actual_size: int,
        expected_hash: str,
        actual_hash: str,
    ) -> None:
        self.relative_path = relative_path
        self.expected_size = expected_size
        self.actual_size = actual_size
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash

        super().__init__(
            "Scanned source file changed before parsing: "
            f"{relative_path!r}; "
            "expected size/hash="
            f"{expected_size}/{expected_hash}, "
            "actual size/hash="
            f"{actual_size}/{actual_hash}.",
        )
