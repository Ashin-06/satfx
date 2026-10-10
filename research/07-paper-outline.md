# 07 · Paper Plan

**Working title:** "Off the Grid, On the Record? Forensic Traces and Orbital Corroboration of Satellite Messaging on Smartphones"

**Venues:** DFRWS USA/EU; FSI: Digital Investigation; a short tool paper for the corroboration method.

## Outline
1. Introduction: satellite texting on mainstream phones; SAR and criminal cases; the missing artifacts
2. Background: Globalstar/Apple, Skylo/Google, Starlink DTC/T-Mobile, Iridium/Garmin
3. Related work: messaging forensics, sysdiagnose, satellite-segment forensics
4. Method: differential extraction protocol; orbital corroboration (SGP4, TEME→ECEF, masks, element age)
5. Results: artifacts per feature (or their absence, which is itself a finding); corroboration on ground-truth sessions; element-age sensitivity
6. Tool: `satfx` (sms.db transport audit, SQLite diff, sweep, corroboration), validation against Skyfield
7. Discussion: what examiners can and cannot conclude; guidance for tool vendors (label satellite transport)
8. Conclusion

## Contributions
1. First systematic search for satellite-messaging artifacts on iOS and Android, with a reusable differential method.
2. Orbital corroboration as a forensic consistency test, validated against an independent library.
3. Open-source `satfx`.
