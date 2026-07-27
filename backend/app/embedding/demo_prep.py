"""Script to scan a directory, filter out non-python files, embed all python files, and upsert to Qdrant."""

from pathlib import Path
import sys

from app.embedding.embedding_pipeline import run_embedding_pipeline
from app.embedding.utils import scan_python_files


def main() -> None:
    # 1. Determine target directory from CLI argument or default
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1]).resolve()
    else:
        # Default to app directory
        target_dir = Path(r"C:\Hieu\TTTN\source-context\backend\app").resolve()

    print("================================================================")
    print(f"  SCANNING & EMBEDDING DIRECTORY: {target_dir}")
    print("================================================================")

    if not target_dir.exists():
        print(f"Error: Target path '{target_dir}' does not exist.")
        return

    # 2. Scan and filter out non-Python files & ignored directories (.venv, git, etc.)
    py_files = scan_python_files(target_dir)
    print(f"\nFound {len(py_files)} Python files to process in {target_dir}:")
    for f in py_files:
        print(f"  - {f.relative_to(target_dir) if target_dir.is_dir() else f.name}")

    if not py_files:
        print("No Python files found to embed.")
        return

    print("\nStarting full directory embedding pipeline...")
    batches = run_embedding_pipeline(
        source_paths=py_files,
        batch_size=50,
    )

    total_embedded = sum(len(b) for b in batches)
    print("\n================================================================")
    print(
        f"  COMPLETED: Embedded {total_embedded} nodes from {len(py_files)} files across {len(batches)} batches."
    )
    print("  Points and metadata payloads have been stored into Qdrant DB.")
    print("================================================================\n")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
