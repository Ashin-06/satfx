import hashlib
from pathlib import Path

import pytest
from test_sms import make_db

from satfx import corroborate

GS = Path(__file__).parent / "fixtures" / "globalstar.tle"


def test_csv_events_verdicts(tmp_path):
    ev = tmp_path / "events.csv"
    ev.write_text("time_utc,lat,lon,label\n"
                  "2026-10-09T12:00:00Z,37.0,-120.0,california\n"
                  "2026-10-09T12:00:00Z,89.9,0.0,north pole\n", encoding="utf-8")
    rep = corroborate.run(corroborate.events_from_csv(str(ev)), str(GS), mask=10, window_min=5)
    by = {r["label"]: r for r in rep["events"]}
    assert by["california"]["verdict"] == "in view" and by["california"]["in_view"] >= 1
    assert by["north pole"]["verdict"] == "no satellite in view within the window"
    a = rep["assumptions"]
    assert a["elements_sha256"] == hashlib.sha256(GS.read_bytes()).hexdigest() and a["satellites"] == 28


def test_bad_csv_reports_line(tmp_path):
    ev = tmp_path / "events.csv"
    ev.write_text("time_utc,lat,lon\n2026-10-09T12:00:00,1,2\n", encoding="utf-8")  # no zone
    with pytest.raises(ValueError, match="line 2"):
        corroborate.events_from_csv(str(ev))


def test_events_from_sms_with_filter(tmp_path):
    db = tmp_path / "sms.db"
    make_db(str(db))
    evs = corroborate.events_from_sms(str(db), 37.0, -120.0)
    assert len(evs) == 5 and all(e["lat"] == 37.0 for e in evs)
    since = corroborate._when("2025-10-01T08:26:42Z")
    assert len(corroborate.events_from_sms(str(db), 37.0, -120.0, since=since)) == 3


def test_renderers(tmp_path):
    ev = tmp_path / "e.csv"
    ev.write_text("time_utc,lat,lon,label\n2026-10-09T12:00:00Z,37,-120,<b>x</b>\n", encoding="utf-8")
    rep = corroborate.run(corroborate.events_from_csv(str(ev)), str(GS), window_min=1)
    h = corroborate.to_html(rep)
    assert "&lt;b&gt;x&lt;/b&gt;" in h and "not proof" in h
    assert corroborate.to_csv(rep).splitlines()[0].startswith("label,time_utc")
    assert '"elements_sha256"' in corroborate.to_json(rep)
