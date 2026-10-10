# 02 · Satellite Services on Phones (Oct 2026)

| Service | Phones | Network | Orbit | What it carries |
|---|---|---|---|---|
| Apple Emergency SOS via satellite | iPhone 14+ (and Watch Ultra 3) | **Globalstar** | LEO ~1,414 km, 52° inclination | SOS questionnaire, location (incl. altitude), battery, Medical ID; to a PSAP or Apple relay centre |
| Apple Find My via satellite | iPhone 14+ | Globalstar | LEO | location share |
| Apple Roadside Assistance via satellite | iPhone 14+ (US, some countries) | Globalstar | LEO | text to provider |
| Apple Messages via satellite | iPhone 14+, iOS 18+ (US, Canada, Japan; Mexico 18.4+) | Globalstar | LEO | iMessage (end-to-end encrypted) and SMS (carrier must support) |
| Pixel Satellite SOS | Pixel 9+, Pixel Watch 4/5 | **Skylo** (operator partners), Garmin Response as emergency centre | GEO (Skylo uses partners' geostationary L/S-band satellites) | SOS questionnaire, location; Google Messages must be default |
| Samsung satellite (Galaxy S25 and later, carrier-dependent) | Galaxy | Skylo / carrier | GEO / LEO | messaging, SOS |
| T-Mobile T-Satellite | many recent phones incl. iPhone | **Starlink direct-to-cell** | LEO ~360 km (V2 Mini DTC payload) | SMS, then MMS/data for some apps; appears as the carrier network |
| Garmin inReach (separate device, often paired to phone) | Garmin devices + app | **Iridium** | LEO ~780 km, 86.4° | messages, tracks, SOS |

Sources: Apple support pages, Google/Skylo announcements, satellite press (see [sources](sources.md)). Constellation altitudes are public orbital facts; they are not needed by the tool, which uses the TLEs directly.

## Forensic consequences
- **Sky view is required.** Apple tells users the iPhone needs a clear view of the sky and horizon; LEO links need the satellite above the local horizon, and in practice above an elevation mask (trees, terrain).
- **The constellation follows the service.** An iPhone SOS needs a Globalstar satellite in view, a T-Satellite text needs a Starlink DTC satellite, Pixel SOS needs line of sight to a GEO satellite. So the claim "sent via satellite at time T from place P" can be tested against orbital mechanics.
- **Encryption:** satellite iMessages are end-to-end encrypted; content lives on the endpoints, not in transit records.
- **Carrier records:** T-Satellite traffic is carrier traffic, so carrier records may show it (legal process).
- **Starlink DTC satellites** are not separated from the main Starlink group in public element sets; a check against the whole Starlink group over-states DTC coverage. Report that.
