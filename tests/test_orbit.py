from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sgp4.api import Satrec

from satfx import orbit

FIX = Path(__file__).parent / "fixtures"
T0 = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)  # fixture element epoch is 9 Oct 2026


def test_geometry_analytic():
    # A point 1000 km straight above the observer is at zenith.
    ox, oy, oz = orbit.observer_ecef(0, 0, 0)
    _, el, rng = orbit.look_ecef((ox + 1000, oy, oz), 0, 0)
    assert el == pytest.approx(90, abs=1e-6) and rng == pytest.approx(1000, abs=1e-6)
    # Directly above a point 90 deg east, as seen from (0, 0): on/below the horizon.
    _, el, _ = orbit.look_ecef((0, orbit.WGS84_A + 1000, 0), 0, 0)
    assert el < 0
    # Due north along the meridian, low: azimuth ~0.
    ox, oy, oz = orbit.observer_ecef(10, 0, 0)
    az, el, _ = orbit.look_ecef((ox - 50, oy, oz + 500), 10, 0)
    assert (az < 1 or az > 359) and 0 < el < 90


def test_load_tle_fixtures():
    gs = orbit.load(FIX / "globalstar.tle")
    ir = orbit.load(FIX / "iridium-NEXT.tle")
    assert len(gs) == 28 and gs[0][0].startswith("GLOBALSTAR")
    assert len(ir) > 60
    assert orbit.epoch(gs[0][1]).year == 2026


@pytest.mark.parametrize("group,lat,lon,alt", [
    ("globalstar.tle", 37.0, -120.0, 0),     # California
    ("globalstar.tle", -33.9, 151.2, 50),    # Sydney
    ("iridium-NEXT.tle", 64.8, -147.7, 130), # Fairbanks
])
def test_matches_skyfield(group, lat, lon, alt):
    skyfield = pytest.importorskip("skyfield.api")
    ts = skyfield.load.timescale(builtin=True)
    lines = [ln for ln in (FIX / group).read_text().splitlines() if ln.strip()]
    obs = skyfield.wgs84.latlon(lat, lon, elevation_m=alt)
    checked = 0
    for minutes in (0, 37, 211):
        when = T0 + timedelta(minutes=minutes)
        t = ts.from_datetime(when)
        for i in range(0, len(lines), 3):
            name, l1, l2 = lines[i].strip(), lines[i + 1], lines[i + 2]
            ref = (skyfield.EarthSatellite(l1, l2, name, ts) - obs).at(t)
            alt_ref, az_ref, dist = ref.altaz()
            mine = orbit.look(Satrec.twoline2rv(l1, l2), when, lat, lon, alt)
            assert mine[1] == pytest.approx(alt_ref.degrees, abs=0.1), name
            assert mine[2] == pytest.approx(dist.km, rel=1e-4), name
            if alt_ref.degrees < 80:  # azimuth is ill-conditioned near zenith
                d = (mine[0] - az_ref.degrees + 180) % 360 - 180
                assert abs(d) < 0.1, name
            checked += 1
    assert checked > 50


def test_coverage_window_and_verdicts():
    gs = orbit.load(FIX / "globalstar.tle")
    r = orbit.coverage(gs, T0, 37.0, -120.0, mask=10, window_min=10, step_s=60)
    assert r["satellites_loaded"] == 28 and len(r["window"]["series"]) == 21
    assert r["verdict"].startswith("in view") == bool(r["in_view_now"])
    assert r["element_age_days"]["max"] < 3 and not r["stale_elements"]
    # Globalstar's 52 deg inclination leaves the poles without coverage: nothing in view at the North Pole.
    pole = orbit.coverage(gs, T0, 89.9, 0.0, mask=10, window_min=10, step_s=60)
    assert pole["verdict"] == "no satellite in view within the window" and pole["nearest_in_view_offset_s"] is None
    # Element sets a month older than the event are flagged stale.
    later = orbit.coverage(gs, T0 + timedelta(days=30), 37.0, -120.0, window_min=1)
    assert later["stale_elements"]


def test_naive_time_rejected():
    gs = orbit.load(FIX / "globalstar.tle")
    with pytest.raises(ValueError):
        orbit.in_view(gs, datetime(2026, 10, 9, 12, 0), 0, 0)
