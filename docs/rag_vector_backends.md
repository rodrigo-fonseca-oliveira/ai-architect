# RAG Vector Backends (Roadmap)

This project defaults to a simple, deterministic RAG for tests and local development. When you enable LangChain mode, we use Chroma as the default persistent vector store in embedded (in‑process) mode.

For production‑grade scale and availability, you may opt into a managed vector DB like Pinecone. This document captures the plan and env toggles for a future iteration.

## Current defaults
- Retrieval backend (feature‑gated):
  - LC_RAG_BACKEND=deterministic|langchain (default: deterministic for CI stability)
- Vector store (LangChain mode):
  - LC_VECTOR_BACKEND=chroma (default)
  - VECTORSTORE_PATH=./.local/vectorstore (Chroma persistence path)
- Docs corpus:
  - DOCS_PATH=./docs (mount a different folder in docker‑compose or override via env)

## Pinecone (planned)
- Goal: provide a drop‑in alternative to Chroma when LC_RAG_BACKEND=langchain for teams that need managed scale, HA, and operational tooling.
- Proposed env flags:
  - LC_VECTOR_BACKEND=pinecone
  - PINECONE_API_KEY=...
  - PINECONE_ENVIRONMENT=...   # e.g., gcp-starter
  - PINECONE_INDEX_NAME=ai-risk-monitor
  - (Optional) PINECONE_NAMESPACE=default
- Behavior:
  - If LC_RAG_BACKEND=langchain and LC_VECTOR_BACKEND=pinecone, initialize a Pinecone index via LangChain’s Pinecone integration using the configured embedding model.
  - If credentials are missing or initialization fails, gracefully fall back to Chroma; if Chroma is unavailable, fall back to the deterministic retriever to preserve uptime and test determinism.

## Embeddings
- EMBEDDINGS_PROVIDER=openai|local (default: local for deterministic tests)
- OPENAI_API_KEY=... (required for OpenAI embeddings)
- LLM_MODEL or EMBEDDING_MODEL may be used to select specific models depending on provider.

## Operational notes
- Local/dev/test:
  - Keep LC_RAG_BACKEND=deterministic (or langchain+chroma) for zero‑ops workflows.
  - Use scripts/ingest_docs.py to populate the vector store.
- Production:
  - Consider LC_RAG_BACKEND=langchain with LC_VECTOR_BACKEND=pinecone for scale.
  - Monitor costs and index sizes; apply namespace sharding for multi‑tenant needs.

## Migration plan (later)
1) Introduce LC_VECTOR_BACKEND with default chroma and optional pinecone.
2) Add Pinecone client wiring in app/services/langchain_rag.py behind env flags.
3) Extend scripts/ingest_docs.py to support Pinecone ingestion.
4) Provide a minimal diagnostic route or script to list collection/index counts across backends.

## Safety and fallbacks
- All backends are optional. The application must continue to operate with deterministic retrieval when flags or credentials are missing.
- Tests remain deterministic by default (no network).
