# Threat model

What the analysis service protects, from whom, and what is still open. Written for the 1.0.0 code;
nobody independent has reviewed it.

## What it protects

| Asset | Where it lives |
|---|---|
| Coverage verdicts and transport audits that may be cited in a case | API responses and the `analyses` table |
| Submitted evidence (sms.db files, claimed times and places) | request bodies and a temporary file removed after each request; never stored |
| API keys | callers hold the key; the service holds only SHA-256 hashes |

A wrong verdict matters most: saying a satellite was in view when it was not, or hiding an
unusual transport value.

## Trust boundaries

1. **Examiner → service.** sms.db files come from seized phones and may be crafted.
2. **Element sets.** The caller chooses them; the result names their SHA-256 so the choice can be
   checked later.

## Threats and what stops them

| Threat | Mitigation | Residual risk |
|---|---|---|
| A crafted sms.db runs code or writes through SQLite | Opened read-only (immutable, or a temporary copy when a `-wal` is present) with `trusted_schema = OFF`; only the `message`, `handle` and chat tables are read, with a fixed column list | SQLite parser bugs |
| Hostile table names break queries (CLI diff) | Identifiers are quoted with doubled quotes | — |
| A request burns CPU for hours | Coordinates, mask, window and event count are bounded, and each request is capped at 8 million satellite positions | Concurrent heavy requests still share the CPU |
| Stale or wrong element sets give a misleading verdict | Every result reports element age and flags stale sets; TLE input carries a warning about missing 6-digit catalog numbers | Choosing the right element set for the date is the examiner's job |
| A verdict is over-read | Reports state that coverage shows consistency with a satellite link, never that a message was sent | — |
| Someone reads the log or submits evidence | API keys with roles; no CORS unless listed | Every `viewer` sees every analysis |
| Evidence leaks through errors or logs | Validation errors don't echo input; unhandled errors return only a request ID | — |
| Upload flooding | 200 MB body cap, per-client rate limit | Rate limit is per process |

## Not covered

- Terrain, buildings and antenna patterns.
- Signing reports or anchoring the log.
- TLS (terminate it at the ingress).
