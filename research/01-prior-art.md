# 01 · Prior Art and the Gap

Searched 10 Oct 2026: web (standard + extended), iLEAPP/ALEAPP/LEAPPs, DFIR blogs, Forensic Focus, IEEE S&P 2026 posters, GitHub.

## What exists
| Work | Covers | Missing |
|---|---|---|
| [LEAPPs](https://leapps.org/) (iLEAPP, ALEAPP) | hundreds of iOS/Android artifacts | **no satellite messaging or satellite SOS module** |
| [ChatExportKnowledge](https://github.com/ChatExport/ChatExportKnowledge) (sms.db schema notes iOS 11-26) | `message.service` values `iMessage`, `SMS`, `RCS`; advice to pass unknown values through | **no satellite value documented** |
| [Magnet Forensics, *The Meaning of Messages*](https://www.magnetforensics.com/blog/the-meaning-of-messages/) | sms.db tables, `message_summary_info` | nothing on satellite |
| [S&P 2026 poster: taxonomy for satellite digital forensics](https://www.ieee-security.org/TC/SP2026/downloads/posters/sp2026posters-final15.pdf) | forensics of satellites and ground segments | not consumer phones |
| [Apple: About Messages via satellite](https://support.apple.com/en-us/120930) | feature behaviour | no artifacts |
| sysdiagnose / unified-log guides ([Elcomsoft](https://blog.elcomsoft.com/2025/06/extracting-and-analyzing-apple-unified-logs/), [hack.lu 2023](https://pretalx.com/hack-lu-2023/talk/YXMSQV/)) | log collection | no satellite subsystem identified |
| Android `bugle_db` guides ([Forensafe](https://www.forensafe.com/blogs/android-google-messages.html), [Magnet](https://www.magnetforensics.com/blog/android-messaging-forensics-sms-mms-and-beyond/)) | Google Messages tables | no satellite field |

## The gap
Three extended searches found **no documented artifact** that marks a message, SOS session or location share as sent over satellite, on iOS or Android. Tools parse these messages as ordinary iMessage/SMS/RCS, so a satellite message looks like any other text.

## Why it matters
- Search and rescue, missing persons, wilderness deaths, alibis: "was the phone off-grid, and did it really send that from there?"
- A satellite message implies the phone had open sky **at a place with no cell coverage**, and that a satellite was overhead at that moment. Both are checkable.
- The features are spreading fast: iPhone 14+ (Globalstar, 2022), iOS 18 Messages via satellite, Pixel 9 Satellite SOS (Skylo/Garmin, 2024), T-Mobile T-Satellite on Starlink direct-to-cell (2025), Apple Watch Ultra 3.

## Gap statement
> Consumer phones now send texts, SOS and location over satellite, but no public work identifies which on-device artifacts record this, and forensic tools present these messages as ordinary texts. We (1) give a controlled method to discover the artifacts by differential extraction, (2) release tooling for that discovery, and (3) add an independent check: whether a satellite of the right constellation was actually in view at the claimed time and place, computed from public orbital elements.
