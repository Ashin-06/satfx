"""Satellite visibility from public orbital elements (method: research/04).

SGP4 (via the `sgp4` package) gives TEME positions; we rotate by GMST to Earth-fixed and compute
topocentric azimuth/elevation for a WGS-84 observer. Polar motion, the equation of the equinoxes and
UT1-UTC are ignored: arcsecond-level effects, irrelevant against a degree-level elevation mask.
"""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sgp4 import omm
from sgp4.api import Satrec, jday
from sgp4.propagation import gstime

WGS84_A = 6378.137                  # km
WGS84_F = 1 / 298.257223563
_E2 = WGS84_F * (2 - WGS84_F)


def load(path: str) -> list[tuple[str, Satrec]]:
    """Read element sets: 2- or 3-line TLE text, or CelesTrak/OMM JSON (list of OMM dicts)."""
    text = Path(path).read_text(encoding="utf-8-sig").strip()
    sats = []
    if text.startswith("["):
        for fields in json.loads(text):
            sat = Satrec()
            omm.initialize(sat, fields)
            sats.append((fields.get("OBJECT_NAME") or str(fields.get("NORAD_CAT_ID")), sat))
        return sats
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    i = 0
    while i < len(lines):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            name, l1, l2 = lines[i][2:7].strip(), lines[i], lines[i + 1]
            i += 2
        elif i + 2 < len(lines) and lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
            name, l1, l2 = lines[i].strip(), lines[i + 1], lines[i + 2]
            i += 3
        else:
            raise ValueError(f"unrecognised element-set line {i + 1}: {lines[i][:40]!r}")
        sats.append((name, Satrec.twoline2rv(l1, l2)))
    return sats


def epoch(sat: Satrec) -> datetime:
    jd = sat.jdsatepoch + sat.jdsatepochF
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - 2440587.5)


def observer_ecef(lat: float, lon: float, alt_m: float = 0.0) -> tuple[float, float, float]:
    """WGS-84 geodetic (degrees, metres) -> Earth-fixed km."""
    p, l = math.radians(lat), math.radians(lon)
    n = WGS84_A / math.sqrt(1 - _E2 * math.sin(p) ** 2)
    h = alt_m / 1000
    return ((n + h) * math.cos(p) * math.cos(l), (n + h) * math.cos(p) * math.sin(l), (n * (1 - _E2) + h) * math.sin(p))


def look_ecef(sat_ecef, lat: float, lon: float, alt_m: float = 0.0) -> tuple[float, float, float]:
    """Azimuth (deg, from north, clockwise), elevation (deg), range (km) of an Earth-fixed point."""
    ox, oy, oz = observer_ecef(lat, lon, alt_m)
    dx, dy, dz = sat_ecef[0] - ox, sat_ecef[1] - oy, sat_ecef[2] - oz
    p, l = math.radians(lat), math.radians(lon)
    e = -math.sin(l) * dx + math.cos(l) * dy
    n = -math.sin(p) * math.cos(l) * dx - math.sin(p) * math.sin(l) * dy + math.cos(p) * dz
    u = math.cos(p) * math.cos(l) * dx + math.cos(p) * math.sin(l) * dy + math.sin(p) * dz
    rng = math.sqrt(dx * dx + dy * dy + dz * dz)
    return math.degrees(math.atan2(e, n)) % 360, math.degrees(math.atan2(u, math.hypot(e, n))), rng


def _utc(when: datetime) -> datetime:
    if when.tzinfo is None:
        raise ValueError("time must be timezone-aware (UTC)")
    return when.astimezone(timezone.utc)


def look(sat: Satrec, when: datetime, lat: float, lon: float, alt_m: float = 0.0):
    """(az, el, range_km) of a satellite at `when`, or None if SGP4 reports an error (e.g. decayed)."""
    t = _utc(when)
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
    err, r, _v = sat.sgp4(jd, fr)
    if err:
        return None
    g = gstime(jd + fr)
    c, s = math.cos(g), math.sin(g)
    return look_ecef((c * r[0] + s * r[1], -s * r[0] + c * r[1], r[2]), lat, lon, alt_m)


def in_view(sats, when, lat, lon, alt_m=0.0, mask=10.0) -> list[dict]:
    t = _utc(when)
    out = []
    for name, sat in sats:
        res = look(sat, t, lat, lon, alt_m)
        if res and res[1] >= mask:
            out.append({"name": name, "az": round(res[0], 2), "el": round(res[1], 2), "range_km": round(res[2], 1),
                        "element_age_days": round(abs((t - epoch(sat)).total_seconds()) / 86400, 2)})
    return sorted(out, key=lambda d: -d["el"])


def coverage(sats, when, lat, lon, alt_m=0.0, mask=10.0, window_min=15, step_s=30, stale_days=3.0) -> dict:
    """In-view satellites at `when`, plus how coverage evolved over +/- window_min minutes.

    ponytail: brute-force loop over satellites x steps; ~seconds for the full Starlink group.
    Switch to sgp4.api.SatrecArray (numpy) if large windows become slow.
    """
    t0 = _utc(when)
    ages = [abs((t0 - epoch(s)).total_seconds()) / 86400 for _, s in sats]
    steps = []
    for k in range(-window_min * 60 // step_s, window_min * 60 // step_s + 1):
        t = t0 + timedelta(seconds=k * step_s)
        steps.append((k * step_s, sum(1 for _, s in sats if (r := look(s, t, lat, lon, alt_m)) and r[1] >= mask)))
    covered = [off for off, n in steps if n]
    now = in_view(sats, t0, lat, lon, alt_m, mask)
    return {
        "time_utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "lat": lat, "lon": lon, "alt_m": alt_m, "mask_deg": mask,
        "satellites_loaded": len(sats), "in_view_now": now,
        "verdict": ("in view" if now else "not in view at this time, but in view within the window" if covered
                    else "no satellite in view within the window"),
        "nearest_in_view_offset_s": min(covered, key=abs) if covered else None,
        "window": {"minutes": window_min, "step_s": step_s, "series": steps},
        "element_age_days": {"min": round(min(ages), 2), "max": round(max(ages), 2)} if ages else None,
        "stale_elements": bool(ages) and min(ages) > stale_days,
        "stale_count": sum(a > stale_days for a in ages),
    }
