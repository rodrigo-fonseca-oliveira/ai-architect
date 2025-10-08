# PII detection and configuration

This project includes a simple, deterministic PII detector based on regex and heuristics. It returns masked previews, counts, and a list of detected types without external calls.

Environment variables
- PII_TYPES: comma-separated base types to enable. Default: email,phone,ssn,credit_card,ipv4
  - Additional base types available: ipv6, iban, passport
- PII_LOCALES: comma-separated locales to enable locale-specific patterns (e.g., US,UK,CA,DE)

Request-level filtering
- The /pii endpoint accepts an optional types array in the request body to override enabled base types for that request only (e.g., ["ssn"]). Locales remain configured via PII_LOCALES.

Base patterns
- email: standard username@domain.tld format
- phone: E.164-like and common national formats, supporting separators and parentheses
- ssn: US Social Security Number (NNN-NN-NNNN)
- ipv4 / ipv6: IPv4 and simplified IPv6
- iban: simplified IBAN (country code + alphanumeric body; no checksum validation)
- passport: generic 7–9 alphanumeric (heuristic)
- credit_card: 13–19 digits with spaces/dashes; validated with Luhn

Locale-specific patterns (simplified)
- US
  - postal_us: ZIP or ZIP+4 (NNNNN or NNNNN-NNNN)
  - dl_us: generic 7–9 alphanumeric placeholder (varies by state in reality)
- UK
  - postal_uk: UK postcode (broad simplified)
  - ni_uk: National Insurance number (AA999999A, with allowed letter ranges)
- CA
  - sin_ca: Canadian SIN (very simplified; 9 digits with optional separators)
  - postal_ca: Canadian postal code (A1A 1A1 pattern)
- DE
  - postal_de: 5-digit postal code
  - id_de: generic 9–10 alphanumeric placeholder

Masking behavior
- Detected values are masked with head and tail visible by default (2 chars each). Example:
  - alice@example.com → al******************om
  - 4111 1111 1111 1111 → 41**************11

Performance and determinism
- Patterns are compiled per request to respect dynamic environment changes and keep tests deterministic.
- Input text is capped to 5000 characters to avoid pathological regex costs.

False positives and tuning
- Some locale and generic patterns are simplified and may yield false positives; adjust PII_TYPES/PII_LOCALES accordingly.
- Consider narrowing keywords or adding word boundaries if you extend patterns.

Examples
```
export PII_TYPES="email,phone,ssn,credit_card,ipv4"
export PII_LOCALES="US,UK,CA"
curl -X POST localhost:8000/pii \
  -H "Content-Type: application/json" \
  -H "X-User-Role: analyst" \
  -d '{"text":"Contact bob@example.com, UK NI AB123456C, ZIP 12345-6789"}'
```
