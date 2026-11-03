"""The analysis API: settings, auth, limits, headers, metrics, health, the log and migrations."""
import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_sms import make_db

from satfx import db, ops

KEY = "satfx_" + "x" * 40
HASHED = {f"sha256:{hashlib.sha256(KEY.encode()).hexdigest()}": {"user": "examiner-1", "role": "examiner"}}
GS = (Path(__file__).parent / "fixtures" / "globalstar.tle").read_text(encoding="utf-8")
OMM = (Path(__file__).parent / "fixtures" / "globalstar.json").read_text(encoding="utf-8")
CALIFORNIA = {"time": "2026-10-09T12:00:00Z", "lat": 37.0, "lon": -120.0, "label": "california"}
POLE = {"time": "2026-10-09T12:00:00Z", "lat": 89.9, "lon": 0.0, "label": "north pole"}


def boot(monkeypatch, **env):
    for k in [k for k in os.environ if k.startswith("SATFX_")]:
        monkeypatch.delenv(k)
    for k, v in env.items():
        monkeypatch.setenv(f"SATFX_{k}", v)
    import satfx.api as api

    return importlib.reload(api)


@pytest.mark.parametrize("change, message", [
    ({"SATFX_API_KEYS": None}, "API keys"),
    ({"SATFX_DATABASE_URL": None}, "DATABASE_URL"),
    ({"SATFX_API_KEYS": json.dumps({KEY: {"user": "x", "role": "examiner"}})}, "sha256"),
    ({"SATFX_API_KEYS": json.dumps({"sha256:" + "0" * 64: {"user": "x", "role": "root"}})}, "roles"),
    ({"SATFX_CORS_ORIGINS": "*"}, "CORS"),
])
def test_production_settings_refused(change, message):
    env = {"SATFX_ENV": "production", "SATFX_API_KEYS": json.dumps(HASHED), "SATFX_DATABASE_URL": "sqlite://"}
    assert ops.load_settings(env).production
    env.update(change)
    with pytest.raises(ops.ConfigError, match=message):
        ops.load_settings({k: v for k, v in env.items() if v is not None})


def test_no_public_bind_and_readable_exit():
    with pytest.raises(ops.ConfigError, match="without API keys"):
        ops.load_settings({"SATFX_HOST": "0.0.0.0"})
    env = {k: v for k, v in os.environ.items() if not k.startswith("SATFX_")}
    r = subprocess.run([sys.executable, "-m", "satfx", "serve", "--host", "0.0.0.0"], env=env,
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode != 0 and "without API keys" in r.stderr


def test_analyses_are_logged_across_a_restart(monkeypatch, tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'a.db'}"
    c = TestClient(boot(monkeypatch, DATABASE_URL=url).app)
    v = c.post("/v1/visible", json={"elements": OMM, **CALIFORNIA, "window": 5}).json()
    assert v["verdict"] == "in view" and v["in_view_now"] and "warning" not in v
    assert c.post("/v1/visible", json={"elements": GS, **CALIFORNIA}).json()["warning"]  # TLE caveat
    rep = c.post("/v1/corroborate", json={"elements": GS, "events": [CALIFORNIA, POLE], "window": 5,
                                          "label": "case 4 exhibit 2"}).json()
    by = {r["label"]: r for r in rep["events"]}
    assert by["california"]["verdict"] == "in view"
    assert by["north pole"]["verdict"] == "no satellite in view within the window"
    assert rep["assumptions"]["elements_sha256"] == hashlib.sha256(GS.encode()).hexdigest()
    html = c.post("/v1/corroborate", json={"elements": GS, "events": [CALIFORNIA], "format": "html"})
    assert html.headers["content-type"].startswith("text/html") and "california" in html.text

    make_db(str(tmp_path / "sms.db"))
    body = (tmp_path / "sms.db").read_bytes()
    s = c.post("/v1/sms", content=body, params={"label": "iphone 15"}).json()
    assert s["unrecognised_services"] == ["SyntheticSat"] and len(s["messages"]) == 5
    assert s["inputs"]["sms_db"] == hashlib.sha256(body).hexdigest()

    c = TestClient(boot(monkeypatch, DATABASE_URL=url).app)  # restart
    log = c.get("/v1/analyses").json()["analyses"]
    assert [a["kind"] for a in log] == ["sms", "corroborate", "corroborate", "visible", "visible"]
    got = c.get(f"/v1/analyses/{s['analysis_id']}").json()
    assert got["summary"]["unrecognised_services"] == ["SyntheticSat"] and got["label"] == "iphone 15"
    assert "attributedBody" not in json.dumps(got) and "+1555" not in json.dumps(got)  # messages are not stored
    assert c.get("/v1/analyses/nope").status_code == 404


def test_bad_inputs_are_refused(monkeypatch):
    c = TestClient(boot(monkeypatch).app)
    assert c.post("/v1/visible", json={"elements": "not an element set", **CALIFORNIA}).status_code == 422
    assert c.post("/v1/visible", json={"elements": GS, **CALIFORNIA, "time": "2026-10-09T12:00:00"}).status_code == 422
    assert c.post("/v1/visible", json={"elements": GS, **CALIFORNIA, "lat": 91}).status_code == 422
    assert c.post("/v1/visible", json={"elements": GS, **CALIFORNIA, "window": 10_000}).status_code == 422
    assert c.post("/v1/corroborate", json={"elements": GS, "events": []}).status_code == 422
    assert c.post("/v1/sms", content=b"not sqlite").status_code == 422
    api = boot(monkeypatch)
    api.MAX_POSITIONS = 1000  # 28 satellites x 61 steps x 2 events is 3,416
    big = TestClient(api.app).post("/v1/corroborate", json={"elements": GS, "events": [CALIFORNIA, POLE]})
    assert big.status_code == 422 and "satellite positions" in big.text
    assert c.post("/v1/sms", content=b"SQLite format 3\x00" + b"\0" * 200).status_code == 422


def test_roles_and_metrics(monkeypatch):
    keys = {"k-ex": {"user": "asha", "role": "examiner"}, "k-view": {"user": "vic", "role": "viewer"},
            "k-mon": {"user": "prom", "role": "monitor"}}
    c = TestClient(boot(monkeypatch, API_KEYS=json.dumps(keys)).app)
    body = {"elements": GS, **CALIFORNIA}
    assert c.post("/v1/visible", json=body).status_code == 401
    assert c.post("/v1/visible", json=body, headers={"x-api-key": "wrong"}).status_code == 401
    assert c.post("/v1/visible", json=body, headers={"x-api-key": "k-view"}).status_code == 403
    assert c.post("/v1/visible", json=body, headers={"x-api-key": "k-ex"}).status_code == 200
    log = c.get("/v1/analyses", headers={"authorization": "Bearer k-view"}).json()["analyses"]
    assert log[0]["requested_by"] == "asha"
    assert c.get("/metrics", headers={"x-api-key": "k-ex"}).status_code == 403
    m = c.get("/metrics", headers={"x-api-key": "k-mon"})
    assert m.status_code == 200 and 'satfx_decisions_total{decision="visible_in view"}' in m.text


def test_limits_headers_errors_and_health(monkeypatch):
    c = TestClient(boot(monkeypatch, RATE_LIMIT="3").app)
    codes = [c.get("/v1/analyses").status_code for _ in range(5)]
    assert codes[:3] == [200] * 3 and codes[3:] == [429, 429]
    api = boot(monkeypatch, MAX_BODY_BYTES="500")

    @api.app.get("/boom")
    def boom():
        raise RuntimeError("secret detail: suspect at 37.0,-120.0")

    c = TestClient(api.app)
    assert c.post("/v1/visible", json={"elements": GS, **CALIFORNIA}).status_code == 413

    def chunks():
        for _ in range(10):
            yield b"a" * 100

    assert c.post("/v1/sms", content=chunks()).status_code == 413
    crash = c.get("/boom")
    assert crash.status_code == 500 and "suspect" not in crash.text and crash.json()["request_id"]
    bad = c.post("/v1/visible", json={"elements": ["SECRETTLE"], **CALIFORNIA})
    assert bad.status_code == 422 and "SECRETTLE" not in bad.text
    r = c.get("/v1/analyses", headers={"x-request-id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123" and r.headers["content-security-policy"] == ops.API_CSP
    assert c.get("/healthz").json() == {"status": "ok"}
    assert c.get("/readyz").json()["checks"] == {"database": True}
    monkeypatch.setattr(api.engine, "connect", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    assert c.get("/readyz").status_code == 503


def test_json_logs_carry_request_ids(capsys):
    ops.setup_logging("INFO")
    token = ops.request_id.set("rid-1")
    ops.log.info("hello")
    ops.request_id.reset(token)
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["request_id"] == "rid-1"


def test_migrations_apply_once(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    eng = db.engine(url)
    assert db.migrate(eng) == ["001_init.sql"] and db.migrate(eng) == []
    with eng.connect() as c:
        tables = {r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))}
    assert {"analyses", "schema_migrations"} <= tables
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("SATFX_")}, "SATFX_DATABASE_URL": url}
    out = subprocess.run([sys.executable, "-m", "satfx", "migrate"], env=env, capture_output=True, text=True,
                         timeout=120, check=False)
    assert out.returncode == 0 and "up to date" in out.stdout
