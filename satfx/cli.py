"""satfx command line. Every command only reads its inputs."""
import argparse
import json
import sys
from datetime import datetime, timezone

from satfx import discover, orbit, sms


def _dump(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _when(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise argparse.ArgumentTypeError("time needs a zone, e.g. 2026-10-09T12:00:00Z")
    return t.astimezone(timezone.utc)


def _place(p):
    p.add_argument("--time", required=True, type=_when, help="ISO-8601 with zone, e.g. 2026-10-09T12:00:00Z")
    p.add_argument("--lat", required=True, type=float)
    p.add_argument("--lon", required=True, type=float)
    p.add_argument("--alt", type=float, default=0.0, help="metres above the WGS-84 ellipsoid")
    p.add_argument("--mask", type=float, default=10.0, help="elevation mask, degrees (default 10)")
    p.add_argument("--window", type=int, default=15, help="+/- minutes to scan (default 15)")


def main(argv=None):
    p = argparse.ArgumentParser(prog="satfx", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("visible", help="which satellites were in view at a time and place")
    v.add_argument("--elements", required=True, help="TLE or OMM-JSON file for the constellation")
    _place(v)
    sub.add_parser("sms", help="iOS sms.db: messages with transport audit (read-only)").add_argument("db")
    d = sub.add_parser("diff", help="what changed in a SQLite database between two extractions")
    d.add_argument("before")
    d.add_argument("after")
    sw = sub.add_parser("sweep", help="find satellite-related terms in an extraction (names and contents)")
    sw.add_argument("root")
    sw.add_argument("--term", action="append", help="search term (repeatable); default: built-in list")
    a = p.parse_args(argv)

    if a.cmd == "visible":
        _dump(orbit.coverage(orbit.load(a.elements), a.time, a.lat, a.lon, a.alt, a.mask, a.window))
    elif a.cmd == "sms":
        _dump(sms.read(a.db))
    elif a.cmd == "diff":
        _dump(discover.diff(a.before, a.after))
    elif a.cmd == "sweep":
        _dump(discover.sweep(a.root, a.term))


if __name__ == "__main__":
    sys.exit(main())
