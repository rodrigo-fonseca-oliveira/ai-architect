# Memory (Phase 7)

This service supports short-term conversation memory and long-term semantic memory.

Short-term memory (SQLite-like persistence)
- Controlled by MEMORY_SHORT_ENABLED (default false)
- Stores per user_id + session_id turns: role, content, timestamp
- When turns exceed MEMORY_SHORT_MAX_TURNS (default 10), updates rolling summary
- Audit counters: memory_short_reads, memory_short_writes, summary_updated, memory_short_pruned
- Retention controls (optional):
  - SHORT_MEMORY_RETENTION_DAYS: prune turns older than N days on read (default 0 = disabled)
  - SHORT_MEMORY_MAX_TURNS_PER_SESSION: cap turns per session, evicting oldest beyond N (default 0 = disabled)

Long-term memory (in-process semantic store)
- Controlled by MEMORY_LONG_ENABLED (default false)
- Uses a lightweight in-memory store keyed by user_id, with optional embeddings for relevance
- Functions: ingest facts from answers; retrieve facts to augment question context
- Each fact tracks created_at (epoch seconds)
- Retention/eviction (optional):
  - MEMORY_LONG_RETENTION_DAYS: drop facts older than N days (default 0 = disabled)
  - MEMORY_LONG_MAX_FACTS: keep at most N most recent facts per user (default 0 = disabled)
- Audit counters: memory_long_reads, memory_long_writes, memory_long_pruned

Integration in /query
- Optional session_id accepted in payload
- When enabled, recent turns/summary are prepended to the question (short-term)
- Retrieved long-term facts are added as a contextual preamble
- After answering, writes user and assistant turns; ingests long facts into long-term memory

Configuration
- MEMORY_SHORT_ENABLED: false
- MEMORY_DB_PATH: ./data/memory_short.db
- MEMORY_SHORT_MAX_TURNS: 10
- SHORT_MEMORY_RETENTION_DAYS: 0 (disabled)
- SHORT_MEMORY_MAX_TURNS_PER_SESSION: 0 (disabled)
- MEMORY_LONG_ENABLED: false
- MEMORY_COLLECTION_PREFIX: memory
- MEMORY_LONG_RETENTION_DAYS: 0 (disabled)
- MEMORY_LONG_MAX_FACTS: 0 (disabled)

Privacy and retention
- Use per-user session identifiers to segregate memory
- Consider data retention policies; short-term DB is a local SQLite file by default

Export/Import (long-term)
- GET /memory/long/export?user_id=... (analyst/admin): export raw facts for the user
- POST /memory/long/import?user_id=... with body {"facts": [{"text": "...", "metadata": {...}}]} to import facts (deduped by text hash)
