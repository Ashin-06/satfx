# Runbook

How to deploy and operate the analysis service. Commands assume the repository root.

## Deploy

```bash
docker build -t satfx:1.0.1 .
python -m satfx.ops keygen              # one API key per examiner, viewer and monitor
docker run -d --name satfx -p 8103:8103 -v satfx-data:/data \
  -e SATFX_KEYS_FILE=/run/secrets/satfx-keys.json \
  satfx:1.0.1
curl -fsS http://127.0.0.1:8103/readyz
```

The image runs in production mode as a non-root user with its log in SQLite under `/data`. It
refuses to start, and logs why, without hashed API keys or a database URL. It needs no outbound
network access: callers send the element sets.

## Use

Fetch element sets from close to the event date (CelesTrak OMM JSON, or Space-Track for history)
and keep the file with the case: its SHA-256 is in every result.

```bash
curl -fsS -H "x-api-key: $KEY" -H "content-type: application/json" \
  -d "{\"elements\": $(python -c 'import json;print(json.dumps(open("globalstar.json").read()))'), \
       \"time\": \"2026-10-09T12:00:00Z\", \"lat\": 37, \"lon\": -120}" http://127.0.0.1:8103/v1/visible
curl -fsS -H "x-api-key: $KEY" --data-binary @sms.db "http://127.0.0.1:8103/v1/sms?label=iphone%20A"
```

`POST /v1/corroborate` takes `elements` and a list of `events` (`time`, `lat`, `lon`, optional
`alt_m` and `label`), with `format` `json`, `csv` or `html`.

## Configure

| Variable | Required in production | Meaning |
|---|---|---|
| `SATFX_ENV` | — | `development` (default) or `production` |
| `SATFX_API_KEYS` / `SATFX_KEYS_FILE` | yes | JSON `{"sha256:<hex>": {"user": "...", "role": "..."}}`. Roles: `examiner` (analyse, read), `viewer`, `monitor`, `admin` |
| `SATFX_DATABASE_URL` | yes | the analysis log: `sqlite:////data/satfx.db` or `postgresql://...` |
| `SATFX_HOST`, `SATFX_PORT` | — | default `127.0.0.1:8103`; any other address needs API keys |
| `SATFX_RATE_LIMIT`, `SATFX_MAX_BODY_BYTES` | — | default 120/min per client, 200,000,000 bytes |
| `SATFX_CORS_ORIGINS` | — | comma-separated origins allowed to call the API from a browser |

## Watch

- `GET /healthz`; `GET /readyz` (database); `GET /metrics` (role `monitor`): requests, latency,
  errors, `satfx_decisions_total{decision="visible_*|event_*|unusual_transport"}`.
- `unusual_transport` counts sms.db files with a service value other than iMessage, SMS or RCS:
  those are the leads worth a closer look.

## Rotate keys

Add the new API key hash, restart, hand over the key, remove the old hash, restart.

## Back up and restore

Back up the log like any SQLite or Postgres database (`python -m satfx migrate` creates the schema
on a fresh one).

## Incidents

1. **Leaked API key.** Remove its hash and restart; list that user's entries.
2. **A verdict is challenged.** Find the entry, check its element-set hash against the file kept
   with the case, and re-run with the same file and version.
