# 03 · Finding the Artifacts: Differential Extraction

No source documents the on-device traces of satellite use, so they have to be found. The method is a controlled before/after comparison on lab phones. The `satfx diff` and `satfx sweep` commands exist for exactly this.

## Candidate locations to watch (hypotheses, not findings)
| Platform | Candidate | Why |
|---|---|---|
| iOS | `HomeDomain/Library/SMS/sms.db` (+ `-wal`): `message.service`, `message_summary_info`, any new column | satellite iMessage/SMS land in Messages; iOS 18 already added `RCS` to `service` |
| iOS | `Library/Caches/com.apple.routined/Cache.sqlite`, `consolidated.db` | location during the session |
| iOS | KnowledgeC / Biome streams | app and feature usage |
| iOS | unified log / sysdiagnose | connection attempts, satellite pointing UI; strings to sweep for: `satellite`, `Globalstar`, `stewie` (reported Apple project codename) |
| iOS | Find My caches | "share location via satellite" |
| Android | `com.google.android.apps.messaging/databases/bugle_db` | Satellite SOS requires Google Messages as default SMS app |
| Android | `com.google.android.apps.safetyhub` / Personal Safety app data | SOS flows |
| Android | telephony / `mmssms.db`, `dumpsys` output | T-Satellite appears as the carrier network |

## Protocol (per platform, per feature)
1. Fresh lab phone, logical + full-file-system baseline extraction (E0).
2. Use one feature once with a recorded ground truth (UTC time, GPS fix from a separate receiver, sky photo): Apple **demo mode** first (connects to a real satellite without calling emergency services), then a Messages-via-satellite text to a lab phone.
3. Extraction E1 immediately; sysdiagnose the same day.
4. `satfx diff E0/sms.db E1/sms.db` (and every changed database); `satfx sweep E1/` for satellite terms.
5. Record every new table, column, value and row. Repeat 3x. Anything stable becomes an artifact; publish the schema evidence.
6. Run `satfx corroborate` for the session with the ground-truth location: the constellation must be in view.

Never use Emergency SOS for real in a test. Apple's demo mode and Google's equivalent exist for this.
