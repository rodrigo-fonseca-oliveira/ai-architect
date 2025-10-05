# Retrieval improvements: multi-query and hyDE

- Flags:
  - RAG_MULTI_QUERY_ENABLED (default: false)
  - RAG_MULTI_QUERY_COUNT (default: 3)
  - RAG_HYDE_ENABLED (default: false)

Behavior when enabled (legacy retriever path):
- reformulate_queries: generates simple deterministic variants (base, key-terms, rephrase)
- retrieve_multi: queries each variant (and an optional hyDE variant) and merges citations, deduping by source+page.

Notes:
- LC_RAG_ENABLED path is left unchanged in this iteration.
- Deterministic tests use EMBEDDINGS_PROVIDER=stub.
