# Auditing & Retention

## Audit writes
- Function: app.utils.audit.write_audit
- Non-blocking behavior: DB errors are caught, transaction rolled back, and error logged. API flow continues.
- Fields include: request_id, endpoint, user_id, created_at, tokens_prompt/completion, cost_usd, latency_ms, compliance_flag, prompt_hash, response_hash.

## Database
- SQLite by default; configure DB_URL for other engines.
- Local DB files are ignored by Git; do not commit audit.db or journals.

## Retention
- Script: scripts/sweep_retention.py
- Usage: python scripts/sweep_retention.py
- Recommended to run periodically (cron/k8s job) depending on policy.
