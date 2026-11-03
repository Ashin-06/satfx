# Changelog

All notable changes to this project. Versions follow [semantic versioning](https://semver.org/).

## 1.0.0 — 2026-11-03

### Added
- An analysis API (`satfx serve`): `POST /v1/visible`, `POST /v1/corroborate` (JSON, CSV or HTML),
  `POST /v1/sms` (transport audit of an uploaded sms.db) and `GET /v1/analyses[/{id}]`. Callers
  send the element sets they rely on. Evidence is not stored; each analysis records its input
  SHA-256s, the counts found and who asked, in SQLite or Postgres with numbered migrations
  (`satfx migrate`). Each request is capped at 8 million satellite positions.
- Settings from `SATFX_*` environment variables, checked at startup; production refuses to start
  without hashed API keys and a database. Roles on keys, rate limit, body cap, security headers,
  JSON logs with request IDs, `/healthz`, `/readyz` and Prometheus `/metrics`.
- `pyproject.toml` 1.0.0 (Python 3.12+), pinned lock files, a container image (slim, non-root,
  health check), CI with ruff, bandit, pip-audit and coverage (it replaces the old test workflow
  and keeps its import-order check and warnings-as-errors). Skyfield is now a dev dependency, so
  the cross-check of the orbit code against it runs in CI instead of being skipped.
- `SECURITY.md`, `docs/threat-model.md`, `docs/runbook.md`, MIT licence.

### Fixed
- `diff` quoted table names without escaping, so a database with a `"` in a table name broke it.
- sms.db is opened with `trusted_schema = OFF`, so a crafted database's views and triggers can't
  call SQL functions.

### Unchanged
- Visibility, coverage verdicts and transport audits; the original tests pass unchanged.
