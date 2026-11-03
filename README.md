# SatFX: Forensics of Satellite Messaging on Phones

**Project 3 of 5** · Status: research complete, tool and analysis API built and tested (36 tests), lab work not started
Research cut-off: 10 Oct 2026

## What this is

Phones now text, call for help and share location over satellite: iPhone 14+ via Globalstar (Emergency SOS, Messages via satellite), Pixel 9+ via Skylo (Satellite SOS), T-Mobile T-Satellite via Starlink direct-to-cell. In search-and-rescue, missing-person, wilderness-death and alibi cases, the key question is "was this sent over satellite, from there, at that time?"

Nobody has documented how a phone records that. Forensic tools show these messages as ordinary iMessage/SMS. SatFX:

1. gives a **method to discover the artifacts** on lab phones (before/after differential extraction), plus the tooling for it;
2. audits **`sms.db` transport values** verbatim and flags any value that is not iMessage/SMS/RCS;
3. adds an **independent check from orbital mechanics**: was a satellite of the right constellation actually above the horizon at the claimed time and place? It uses public orbital elements, is validated against an established astronomy library, and runs fully offline.

## Why it is novel
| Exists | Missing |
|---|---|
| iLEAPP/ALEAPP: hundreds of artifacts | no satellite module |
| sms.db schema notes (iOS 11-26) | no satellite transport value documented |
| Satellite-segment forensics (S&P 2026 poster) | not phones |
| Satellite tracking software | not used as forensic corroboration of phone evidence |

## Honest scope
- **No satellite artifact is confirmed yet.** Confirming them needs lab phones in open-sky conditions ([research/03](research/03-artifact-discovery.md), [06](research/06-experiment-plan.md)). The tool does not pretend otherwise: it reports transport values as stored and flags unknown ones.
- Orbital corroboration shows **consistency**, never that a message was sent.

## Repository layout
```
03-satellite-messaging-forensics/
├── README.md
├── research/
│   ├── 01-prior-art.md              searches, gap statement
│   ├── 02-services.md               Apple/Globalstar, Pixel/Skylo, T-Mobile/Starlink, Garmin/Iridium
│   ├── 03-artifact-discovery.md     candidate locations, differential-extraction protocol
│   ├── 04-orbital-corroboration.md  SGP4 method, validation, how to read results
│   ├── 05-legal-ethics.md           never trigger real SOS; reporting as consistency
│   ├── 06-experiment-plan.md        hypotheses H1-H7, lab tasks L1-L6
│   ├── 07-paper-outline.md
│   └── sources.md
├── satfx/
│   ├── orbit.py                     SGP4 visibility, coverage windows, element-age and TLE warnings
│   ├── corroborate.py               per-event verdicts, reproducible inputs, JSON/CSV/HTML
│   ├── sms.py                       iOS sms.db reader with transport audit
│   ├── discover.py                  SQLite before/after diff, term sweep
│   ├── api.py                       analysis API with a log of every analysis
│   ├── ops.py, db.py                settings, API keys, limits, logs, metrics; database and migrations
│   └── cli.py                       `satfx` command
├── docs/                            threat model, runbook
├── tests/                           36 tests; fixtures = real CelesTrak sets (9 Oct 2026)
└── pyproject.toml
```

## Finding so far: TLE data silently drops new satellites
CelesTrak's TLE output for Globalstar returned **28** satellites; its OMM JSON returned **36**. The 8 missing are the newest (6-digit catalog numbers the TLE format cannot hold), about 22% of the constellation. At 70°S 40°E on 9 Oct 2026 13:12 UTC the TLE data shows no satellite in view while the full data shows one, so a TLE-based analysis would wrongly call a satellite message implausible. Details in [research/04](research/04-orbital-corroboration.md). `satfx` warns on every TLE-based result.

## Tool
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.lock -e .   # Linux/macOS: .venv/bin/pip
pytest -q
```
Every command only reads its inputs.

```bash
satfx visible     --elements globalstar.json --time 2026-10-09T12:00:00Z --lat 37 --lon -120
satfx corroborate --elements globalstar.json --events events.csv --format html > corroboration.html
satfx corroborate --elements globalstar.json --sms sms.db --lat 37 --lon -120 --since 2026-10-01T00:00:00Z
satfx sms         sms.db                       # messages with transport audit
satfx diff        e0/sms.db e1/sms.db          # what a satellite session changed (lab protocol)
satfx sweep       extraction/                  # satellite terms in names and contents
```
Get element sets as OMM JSON, from close to the event date: `https://celestrak.org/NORAD/elements/gp.php?GROUP=globalstar&FORMAT=json` (also `iridium-NEXT`, `starlink`; historical sets from Space-Track). Keep the file: its SHA-256 goes into every report.

| Feature | Checked against | Status |
|---|---|---|
| SGP4 visibility (az/el/range) | Skyfield on real Globalstar + Iridium sets, 8,100 comparisons | ✅ max error 0.0023° el, 0.011° az, 42 m |
| TLE and OMM JSON loading | same satellites agree < 0.001; 6-digit gap reproduced | ✅ tests |
| Coverage window, verdicts, element-age flags | analytic cases (pole, stale sets) | ✅ tests |
| sms.db transport audit, attributedBody, mixed s/ns dates | synthetic sms.db per documented schema | ✅ tests; ⏳ real iOS 26 db is lab task L1 |
| SQLite diff, term sweep (UTF-8/16, chunk boundaries) | synthetic before/after databases and files | ✅ tests |
| Corroboration reports with input hashes | real element sets | ✅ tests |
| Speed | 8,960 satellites × 61 steps | 2.0 s |

### Known gaps
- **No satellite artifact on the phone is confirmed yet.** That needs lab phones (L1-L5). Until then the tool reports transport values verbatim and flags unknown ones; it does not claim to detect satellite messages.
- **Android `bugle_db`** is not parsed (schema undocumented for satellite); use `diff` and `sweep`.
- **Starlink direct-to-cell** satellites are not separated in public element sets; a Starlink-group check over-states T-Satellite coverage.
- **No terrain model**: the elevation mask stands in for trees and terrain.
- **Compressed logs** (unified-log `.tracev3`) are not decompressed by `sweep`.

## Analysis API

`satfx serve` (or the container image, `docker build -t satfx .`, see [docs/runbook.md](docs/runbook.md)) puts visibility, corroboration and the sms.db audit behind an API.

| Endpoint | Purpose |
|---|---|
| `POST /v1/visible` | which satellites were in view at a time and place |
| `POST /v1/corroborate` | a coverage verdict per claimed event, as JSON, CSV or HTML |
| `POST /v1/sms` | transport audit of an iOS sms.db sent as the body |
| `GET /v1/analyses`, `/v1/analyses/{id}` | the log: who submitted which inputs (by SHA-256), what was found |
| `GET /healthz`, `/readyz`, `/metrics` | health, readiness and Prometheus metrics |

Callers send the element sets they rely on, so every result names the exact set behind it. Evidence is not stored. Each request is capped at 8 million satellite positions; split larger jobs. API keys carry a role: `examiner`, `viewer`, `monitor`. Create one with `python -m satfx.ops keygen`.

| Variable | Purpose |
|---|---|
| `SATFX_ENV=production` | refuse to start without hashed API keys and a database |
| `SATFX_API_KEYS` / `SATFX_KEYS_FILE` | hashed API keys with roles |
| `SATFX_DATABASE_URL` | the analysis log: `sqlite:///...` or `postgresql://...` |

## Limitations

- No satellite artifact on a phone is confirmed yet; the tool reports transport values as stored and flags unknown ones.
- Coverage shows consistency with a satellite link, never that a message was sent; terrain and buildings are not modelled.
- The analysis log records input hashes but is not signed or hash-chained.
- The methods have not been tested in court, and the code has not had an independent security review.

See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

## Ethics in one line
Lab work uses demo modes only, never a real emergency call, on project phones and accounts. Details in [research/05](research/05-legal-ethics.md).

## License

MIT. See [LICENSE](LICENSE).
