import os
from dotenv import load_dotenv

# Legacy retriever removed; script now validates docs exist and exits.

load_dotenv()

DOCS_PATH = os.getenv("DOCS_PATH", "./examples")


def extract_pdf_text(path: str) -> str:
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise RuntimeError(
            "PyMuPDF (pymupdf) is required for PDF ingestion. Install with `pip install pymupdf`."
        ) from e
    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def chunk_text(text: str, size: int = 1000, overlap: int = 200):
    if size <= 0:
        yield 0, text
        return
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + size)
        yield start, text[start:end]
        if end == n:
            break
        start = max(0, end - overlap)


def main():
    # No vectorstore anymore; treat as validation/no-op.
    if not os.path.isdir(DOCS_PATH):
        raise SystemExit(f"Docs path not found: {DOCS_PATH}")
    # Optionally, touch a marker file to indicate readiness
    print(f"Docs path ready: {DOCS_PATH}")


if __name__ == "__main__":
    main()
