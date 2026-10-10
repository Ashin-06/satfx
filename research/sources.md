# Sources (accessed 10 Oct 2026)

## Services
- Apple, About Messages via satellite: https://support.apple.com/en-us/120930
- Apple, Text via satellite: https://support.apple.com/guide/iphone/text-via-satellite-iphb9262f4dd/ios
- Apple, Use Emergency SOS via satellite: https://support.apple.com/en-hk/HT213426
- Apple, Emergency SOS via satellite launch (Globalstar): https://www.apple.com/newsroom/2022/11/emergency-sos-via-satellite-available-today-on-iphone-14-lineup/
- Google Pixel 9 Satellite SOS (Skylo, Garmin): https://www.satellitetoday.com/connectivity/2024/08/14/google-brings-satellite-sos-feature-to-android-with-pixel-9/ · https://www.skylo.tech/newsroom/skylo-connectivity-enables-new-satellite-sos-feature-on-google-pixel-9-series
- Android 15 satellite messaging status: https://www.androidauthority.com/satellite-messaging-android-15-google-3492088/
- Pixel SOS privacy disclosure: https://phonearena.com/news/google-messages-leak-hints-at-satellite-messaging-allowing-you-to-text-anyone-anywhere_id156929
- T-Mobile / Starlink direct-to-cell: https://www.satelliteinternet.com/providers/starlink/starlink-direct-to-cell/ · https://www.computerworld.com/article/3812353/iphones-on-t-mobile-can-access-starlink-satellite-communications.html
- Apple "Stewie" codename (Gurman via iClarified): https://scour.ing/p/https://www.iclarified.com/98996/apple-developing-satellitepowered-maps-photo-messaging-and-thirdparty-app-support-for-iphone-gurman

## Forensics
- ChatExportKnowledge (sms.db iOS 11-26, transports): https://github.com/ChatExport/ChatExportKnowledge
- Magnet Forensics, The Meaning of Messages: https://www.magnetforensics.com/blog/the-meaning-of-messages/
- LEAPPs: https://leapps.org/
- Elcomsoft unified logs: https://blog.elcomsoft.com/2025/06/extracting-and-analyzing-apple-unified-logs/
- Sysdiagnose for forensics (hack.lu 2023): https://pretalx.com/hack-lu-2023/talk/YXMSQV/
- Forensafe, Google Messages: https://www.forensafe.com/blogs/android-google-messages.html
- S&P 2026 poster, satellite digital forensics taxonomy: https://www.ieee-security.org/TC/SP2026/downloads/posters/sp2026posters-final15.pdf

## Orbital data and models
- CelesTrak GP data and groups: https://celestrak.org/NORAD/elements/ · SupGP: https://celestrak.org/NORAD/elements/supplemental/ · 6-digit catalog / OMM notice on the same site
- `sgp4` (Python, Vallado SGP4): https://pypi.org/project/sgp4/ (v2.27 used)
- Skyfield (validation only): https://rhodesmill.org/skyfield/ (v1.55 used)
- Test fixtures: `tests/fixtures/globalstar.tle`, `tests/fixtures/iridium-NEXT.tle` downloaded from `https://celestrak.org/NORAD/elements/gp.php?GROUP=<group>&FORMAT=tle` on 10 Oct 2026 (epoch 9 Oct 2026)
