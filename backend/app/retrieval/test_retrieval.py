"""Interactive CLI script to test custom natural language queries against CodeRetriever and Qdrant."""

from pathlib import Path
import sys

from app.core.qdrant import QdrantVectorStore, get_qdrant_client
from app.embedding.embedding_pipeline import run_embedding_pipeline
from app.embedding.utils import scan_python_files
from app.retrieval.retriever import CodeRetriever


def main() -> None:
    print("================================================================")
    print("  INTERACTIVE CODE RETRIEVAL TEST (Voyage AI + Qdrant DB)")
    print("================================================================")

    # Re-use single Qdrant client connection (connects to Qdrant Docker service)
    client = get_qdrant_client()
    store = QdrantVectorStore(client=client)

    # 1. Determine target directory from CLI argument or default
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1]).resolve()
    else:
        target_dir = Path(
            r"C:\Hieu\TTTN\source-context\backend\data\sample_data"
        ).resolve()

    # 2. Interactive prompt search loop
    retriever = CodeRetriever(client=client)
    print("Type your natural language search query (or 'exit' / 'quit' to stop):")
    print("-" * 64)

    default_queries = ["The function that extract meta data"]

    for default_q in default_queries:
        print(f"\n[DEMO QUERY]: '{default_q}'")
        results = retriever.retrieve(query=default_q, top_k=3)

        if not results:
            print("  No matching hits found in Qdrant.")
            continue

        for rank, res in enumerate(results, start=1):
            print(
                f"  Rank #{rank} | Similarity Score: {res.score:.4f} | Name: {res.name} ({res.kind})"
            )
            print(f"    File: {res.file_path}")
            print(f"    Signature: {res.signature}")
            if res.summary:
                print(f"    Summary: {res.summary[:150]}...")
            print()

    print("=" * 64)
    print("Interactive mode ready. Enter custom search prompt:")

    # Check if running interactively in terminal or non-interactive pipe
    if not sys.stdin.isatty():
        print("Non-interactive session detected. Exiting demo successfully.")
        return

    while True:
        try:
            query = input("\nSearch Query > ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting search demo. Goodbye!")
                break

            results = retriever.retrieve(query=query, top_k=3)
            if not results:
                print("No matching hits found.")
                continue

            print(f"\nTop {len(results)} Matches for: '{query}':")
            print("=" * 64)

            for rank, res in enumerate(results, start=1):
                print(f"[{rank}] Score: {res.score:.4f} | {res.name} ({res.kind})")
                print(f"    File: {res.file_path}")
                print(f"    Signature: {res.signature}")
                if res.summary:
                    print(f"    Summary: {res.summary}")
                print(f"    Identifiers: {', '.join(res.identifiers[:10])}")
                print("-" * 64)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting search demo. Goodbye!")
            break


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
