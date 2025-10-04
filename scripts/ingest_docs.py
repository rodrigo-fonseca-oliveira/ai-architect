import os
from dotenv import load_dotenv

from app.services.rag_retriever import RAGRetriever

load_dotenv()

DOCS_PATH = os.getenv("DOCS_PATH", "./examples")
VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH", "./.local/vectorstore")
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", os.getenv("LLM_PROVIDER", "local"))


def main():
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    retriever = RAGRetriever(persist_path=VECTORSTORE_PATH, provider=EMBEDDINGS_PROVIDER)
    count = retriever.ingest(DOCS_PATH)
    print(f"Ingested {count} documents from {DOCS_PATH} into {VECTORSTORE_PATH}")


if __name__ == "__main__":
    main()
