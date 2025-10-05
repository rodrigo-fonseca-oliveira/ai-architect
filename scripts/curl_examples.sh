#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
ROLE_HEADER=${ROLE_HEADER:-"-H X-User-Role: analyst"}

# Query grounded RAG
curl -s -X POST "$BASE_URL/query" -H "Content-Type: application/json" -H "X-User-Role: analyst" \
  -d '{"question":"What is GDPR?","grounded":true}' | jq . | sed -n '1,40p'

# Memory status (admin)
curl -s "$BASE_URL/memory/status" -H "X-User-Role: admin" | jq . | sed -n '1,60p'

# Policy navigator
curl -s -X POST "$BASE_URL/policy_navigator" -H "Content-Type: application/json" -H "X-User-Role: analyst" \
  -d '{"question":"Outline GDPR obligations and AI policy considerations for data minimization."}' | jq . | sed -n '1,60p'

# PII remediation
curl -s -X POST "$BASE_URL/pii_remediation" -H "Content-Type: application/json" -H "X-User-Role: analyst" \
  -d '{"text":"Email a@b.com and SSN 123-45-6789 present.","return_snippets":true,"grounded":true}' | jq . | sed -n '1,60p'
