# SatFX: Forensics of Satellite Messaging on Phones

**Project 3 of 5** · Status: research complete, tool in progress, lab work not started
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
```

## Ethics in one line
Lab work uses demo modes only, never a real emergency call, on project phones and accounts. Details in [research/05](research/05-legal-ethics.md).
