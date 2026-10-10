# 04 · Orbital Corroboration

## Question
"The phone sent this via satellite at time T from location P." Was a satellite of the right constellation actually in view?

## Method (implemented in `satfx/orbit.py`)
1. Orbital elements: TLE or OMM for the constellation, **from close to the event date** (CelesTrak current sets; historical sets from Space-Track or CelesTrak archives). SGP4 accuracy decays with distance from the element epoch, so the tool reports the age of every element set and flags any older than 3 days (configurable).
2. Propagate each satellite with **SGP4** (the standard model for TLEs; `sgp4` library by Brandon Rhodes, Vallado's reference implementation) to TEME coordinates.
3. Rotate TEME → Earth-fixed by Greenwich mean sidereal time. Polar motion and the equation of the equinoxes are ignored: the error is arcseconds, irrelevant to a visibility question with a degree-level mask.
4. Observer position from WGS-84 geodetic latitude, longitude, height.
5. Topocentric azimuth, elevation, range. A satellite is in view if elevation ≥ the mask (default 10°; report results for several masks because terrain and trees vary).
6. Over a window (default ±15 min, 30 s steps) report how many satellites were in view and when coverage started and ended, because phone timestamps can be off and users wait for a satellite.

## Validation
- Geometry unit tests with analytic cases (overhead = 90°, opposite side of Earth below horizon).
- Cross-check of azimuth/elevation against **Skyfield** (independent, well-tested astronomy library) on the real Globalstar and Iridium element sets saved in `tests/fixtures/` (CelesTrak, epoch 9 Oct 2026). Measured over 8,100 comparisons (two constellations, five sites from the equator to Antarctica, a full day): max error 0.0023° elevation, 0.011° azimuth, 42 m range. The test suite asserts < 0.1°.

## What a result means
- **In view:** consistent with a satellite link. It does not prove a message was sent.
- **Not in view at any time in the window:** a satellite link from that place and time is implausible for that constellation, so check the timestamp, the location, the claimed service and the element-set age.
- GEO services (Skylo): a GEO satellite is nearly fixed in the sky, so the test becomes "was the GEO satellite above the mask from this latitude/longitude", which fails at high latitudes and behind terrain.
- The tool does not model terrain, buildings or foliage. A mask is a stand-in; site photos or a horizon survey are better.

## Finding: the TLE format silently drops new satellites (10 Oct 2026)
CelesTrak warned that objects catalogued after the 5-digit catalog numbers ran out get 6-digit numbers, which the TLE format cannot hold. Checked directly on the Globalstar group the same day:

| Format | Satellites returned |
|---|---|
| TLE (`FORMAT=tle`) | **28** |
| OMM JSON (`FORMAT=json`) | **36** |

The 8 missing are the newest satellites, GLOBALSTAR M098 to M106 (catalog 100325 to 100332), about **22% of the constellation**. For the 28 satellites present in both, positions agree to within 0.001° and 0.001 km, so the formats are equivalent apart from the gap.

The gap changes verdicts. At 70°S 40°E on 9 Oct 2026 at 13:12 UTC, the TLE set has **no** Globalstar satellite above 10°, while the full set has **GLOBALSTAR M104** in view. An analysis using TLEs would wrongly call a satellite message from there and then implausible.

Consequence for examiners: use OMM JSON (or another format that carries 6-digit catalog numbers) for any event after these launches. `satfx` attaches a warning to every result computed from TLE input. Both fixtures are in `tests/fixtures/`, and the regression tests reproduce this.
