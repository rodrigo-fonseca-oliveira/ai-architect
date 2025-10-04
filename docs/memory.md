# Memory (Phase 7)

This service supports short-term conversation memory and long-term semantic memory.

Short-term memory (SQLite-like persistence)
- Controlled by MEMORY_SHORT_ENABLED (default false)
- Stores per user_id + session_id turns: role, content, timestamp
- When turns exceed MEMORY_SHORT_MAX_TURNS (default 10), updates rolling summary
- Audit counters: memory_short_reads, memory_short_writes, summary_updated

Long-term memory (in-process semantic store)
- Controlled by MEMORY_LONG_ENABLED (default false)
- Uses a lightweight in-memory store keyed by user_id, with optional embeddings for relevance
- Functions: ingest facts from answers; retrieve facts to augment question context
- Audit counters: memory_long_reads, memory_long_writes

Integration in /query
- Optional session_id accepted in payload
- When enabled, recent turns/summary are prepended to the question (short-term)
- Retrieved long-term facts are added as a contextual preamble
- After answering, writes user and assistant turns; ingests long facts into long-term memory

Configuration
- MEMORY_SHORT_ENABLED: false
- MEMORY_DB_PATH: ./data/memory_short.db
- MEMORY_SHORT_MAX_TURNS: 10
- MEMORY_LONG_ENABLED: false
- MEMORY_COLLECTION_PREFIX: memory

Privacy and retention
- Use per-user session identifiers to segregate memory
- Consider data retention policies; short-term DB is a local SQLite file by default
