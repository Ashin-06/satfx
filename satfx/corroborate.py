"""Per-event orbital corroboration with a reproducible record of inputs and assumptions."""
import csv
import hashlib
import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from satfx import orbit, sms


def _when(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError(f"time without a zone: {s!r}")
    return t.astimezone(timezone.utc)


def events_from_csv(path: str) -> list[dict]:
    """CSV with columns time_utc, lat, lon and optional alt_m, label."""
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            try:
                out.append({"label": r.get("label") or f"row {i}", "time": _when(r["time_utc"]),
                            "lat": float(r["lat"]), "lon": float(r["lon"]), "alt_m": float(r.get("alt_m") or 0)})
            except (KeyError, ValueError) as e:
                raise ValueError(f"{path} line {i}: {e}") from None
    return out


def events_from_sms(path: str, lat: float, lon: float, alt_m: float = 0.0,
                    since: datetime | None = None, until: datetime | None = None) -> list[dict]:
    """Messages from sms.db at one claimed location (the examiner supplies the location)."""
    out = []
    for m in sms.read(path)["messages"]:
        if not m["time_utc"]:
            continue
        t = _when(m["time_utc"])
        if (since and t < since) or (until and t > until):
            continue
        out.append({"label": f"sms rowid {m['rowid']} ({m['service'] or 'blank'})", "time": t,
                    "lat": lat, "lon": lon, "alt_m": alt_m})
    return out


def run(events: list[dict], elements_path: str, mask: float = 10.0, window_min: int = 15) -> dict:
    sats = orbit.load(elements_path)
    rows = []
    for e in events:
        c = orbit.coverage(sats, e["time"], e["lat"], e["lon"], e["alt_m"], mask, window_min)
        best = c["in_view_now"][0] if c["in_view_now"] else None
        rows.append({"label": e["label"], "time_utc": c["time_utc"], "lat": e["lat"], "lon": e["lon"],
                     "verdict": c["verdict"], "in_view": len(c["in_view_now"]),
                     "best": f"{best['name']} el {best['el']}" if best else None,
                     "nearest_in_view_offset_s": c["nearest_in_view_offset_s"],
                     "element_age_days": c["element_age_days"], "stale_elements": c["stale_elements"]})
    data = Path(elements_path).read_bytes()
    return {
        "assumptions": {
            "elements_file": str(elements_path), "elements_sha256": hashlib.sha256(data).hexdigest(),
            "elements_format": orbit.elements_format(elements_path),
            "warning": orbit.TLE_WARNING if orbit.elements_format(elements_path) == "tle" else None,
            "satellites": len(sats), "mask_deg": mask, "window_min": window_min, "model": "SGP4, TEME->ECEF by GMST",
            "not_modelled": "terrain, buildings, foliage, device antenna, service availability",
            "meaning": "consistency with a satellite link, not proof that a message was sent",
        },
        "events": rows,
    }


def to_csv(rep: dict) -> str:
    buf = io.StringIO()
    cols = ["label", "time_utc", "lat", "lon", "verdict", "in_view", "best", "nearest_in_view_offset_s",
            "stale_elements"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rep["events"])
    return buf.getvalue()


def to_json(rep: dict) -> str:
    return json.dumps(rep, indent=2, default=str)


def to_html(rep: dict, title: str = "SatFX corroboration") -> str:
    e = lambda v: html.escape("" if v is None else str(v))
    a = rep["assumptions"]
    amp = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in a.items())
    rows = "".join(
        f"<tr class='{'ok' if r['verdict'] == 'in view' else 'bad' if r['verdict'].startswith('no') else 'mid'}'>"
        f"<td>{e(r['label'])}</td><td>{e(r['time_utc'])}</td><td>{e(r['lat'])}, {e(r['lon'])}</td>"
        f"<td>{e(r['verdict'])}</td><td>{e(r['in_view'])}</td><td>{e(r['best'])}</td>"
        f"<td>{e(r['nearest_in_view_offset_s'])}</td><td>{'yes' if r['stale_elements'] else ''}</td></tr>"
        for r in rep["events"])
    return ("<!doctype html><meta charset=utf-8>"
            f"<title>{e(title)}</title><style>body{{font:14px system-ui;margin:1rem}}table{{border-collapse:"
            "collapse;width:100%;margin-bottom:1rem}td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}"
            "th{background:#f0f0f0}.ok td:nth-child(4){color:#176b2c}.bad td:nth-child(4){color:#a3191f}"
            ".mid td:nth-child(4){color:#8a5a00}</style>"
            f"<h1>{e(title)}</h1><h2>Inputs and assumptions</h2><table>{amp}</table>"
            "<h2>Events</h2><table><tr><th>Event</th><th>UTC</th><th>Lat, Lon</th><th>Verdict</th><th>In view</th>"
            f"<th>Highest</th><th>Nearest in-view offset (s)</th><th>Stale elements</th></tr>{rows}</table>")
