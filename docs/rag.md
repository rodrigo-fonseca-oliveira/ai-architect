# Retrieval improvements: multi-query and hyDE

- Flags:
  - RAG_MULTI_QUERY_ENABLED (default: false)
  - RAG_MULTI_QUERY_COUNT (default: 3)
  - RAG_HYDE_ENABLED (default: false)

Behavior:
- LC-backed retrieval is the default and only path.
- Deterministic tests rely on scanning DOCS_PATH text files and merging snippets.
