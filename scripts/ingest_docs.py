import os
from dotenv import load_dotenv

from app.services.rag_retriever import RAGRetriever

load_dotenv()

DOCS_PATH = os.getenv("DOCS_PATH", "./examples")
VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))


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
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    retriever = RAGRetriever(persist_path=VECTORSTORE_PATH, provider=EMBEDDINGS_PROVIDER)

    # Custom ingestion to include PDFs and chunking
    docs = []
    metadatas = []
    ids = []
    for root, _, files in os.walk(DOCS_PATH):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, DOCS_PATH)
            text = None
            if f.lower().endswith((".txt", ".md")):
                with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            elif f.lower().endswith(".pdf"):
                try:
                    text = extract_pdf_text(p)
                except Exception as e:
                    print(f"[warn] failed to extract PDF '{rel}': {e}")
            if not text:
                continue
            for idx, chunk in chunk_text(text, size=1000, overlap=200):
                chunk_id = f"{rel}#chunk-{idx}"
                docs.append(chunk)
                metadatas.append({"source": rel, "offset": idx})
                ids.append(chunk_id)

    if docs:
        embeddings = retriever.emb.embed(docs)
        retriever.collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
        count = len(docs)
    else:
        count = 0

    print(f"Ingested {count} documents from {DOCS_PATH} into {VECTORSTORE_PATH}")


if __name__ == "__main__":
    main()
