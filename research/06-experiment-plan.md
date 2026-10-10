# 06 · Experiment Plan

## Hypotheses
| ID | Hypothesis |
|---|---|
| H1 | A Messages-via-satellite iMessage is stored in `sms.db` with a distinguishing value or flag (new `service` value, `message_summary_info` key, or new column) |
| H2 | A satellite SMS (iOS) is stored as `service = SMS` with no satellite marker |
| H3 | Emergency SOS demo sessions leave traces in the unified log / sysdiagnose and in usage (Biome/KnowledgeC) |
| H4 | Pixel Satellite SOS demo leaves records in Google Messages `bugle_db` or the Personal Safety app |
| H5 | T-Satellite texts are indistinguishable on the handset from terrestrial SMS except by network/cell metadata |
| H6 | For every real satellite session, `satfx corroborate` finds the right constellation in view at the recorded time and place (≥10° mask) |
| H7 | Corroboration with element sets >7 days old still gives the same in-view verdict for LEO at a 10° mask in most cases; quantify disagreement vs fresh sets |

## Lab tasks
| ID | Task |
|---|---|
| L1 | iPhone 15/16 (iOS 26), lab Apple ID; E0 extraction |
| L2 | Emergency SOS demo ×3 at a surveyed open site; E1 + sysdiagnose; `diff`, `sweep` (H3) |
| L3 | Messages via satellite: iMessage and SMS to a lab phone ×3; E2; `diff` (H1, H2) |
| L4 | Pixel 9/10: Satellite SOS demo ×3; extraction; `diff`, `sweep` (H4) |
| L5 | T-Satellite eligible phone: texts in a no-coverage area; extraction (H5) |
| L6 | For every session: `corroborate` with fresh and aged element sets (H6, H7) |

## Metrics
Artifact tables per feature; corroboration agreement rate; effect of element-set age; time offset between the phone's timestamp and the nearest in-view interval.

## Schedule (~10 weeks part-time)
1-2 hardware, plans, ground-truth kit · 3-5 iOS (L1-L3) · 6-7 Android (L4, L5) · 8 corroboration study (L6) · 9-10 write-up, LEAPP plugin PRs for confirmed artifacts.
