# RAG (Retrieval-Augmented Generation)

## Overview
- Vector store path: VECTORSTORE_PATH (e.g., /data/vectorstore)
- Providers:
  - local (SentenceTransformers)
  - openai (requires LLM_API_KEY)
  - stub (deterministic, for tests)

## Ingestion
- Supported file types: .txt, .md
- Idempotent by design: document IDs are SHA256(content + relative path). Re-ingesting the same files will not create duplicates.

### CLI example
- Ingest example docs:
  - python scripts/ingest_docs.py --path ./examples

### Programmatic example
from app.services.rag_retriever import RAGRetriever
retriever = RAGRetriever(persist_path="/data/vectorstore", provider="local")
retriever.ingest("./examples")

## Retrieval
- Method: RAGRetriever.retrieve(query: str, k: int = 3)
- Returns citations with source and snippet.

## Configuration
- EMBEDDINGS_PROVIDER (local|openai|stub)
- EMBEDDINGS_MODEL (e.g., sentence-transformers/all-MiniLM-L6-v2)
- VECTORSTORE_PATH (storage path)
- LC_RAG_ENABLED (default false): when true, grounded queries use the LangChain RetrievalQA path
