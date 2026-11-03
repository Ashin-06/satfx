"""Analysis service: satellite visibility, corroboration and sms.db audits behind an API, with a log.

    POST /v1/visible            which satellites were in view at a time and place [analyse]
    POST /v1/corroborate        a coverage verdict per claimed event [analyse]
    POST /v1/sms                transport audit of an iOS sms.db (body = the database file) [analyse]
    GET  /v1/analyses[/{id}]    the analysis log: who submitted which inputs (by SHA-256), what was found [read]
    GET  /healthz, /readyz, /metrics

Callers send the orbital elements they rely on (TLE or OMM JSON, e.g. from CelesTrak for the date
in question), so every result names the exact element set behind it. Evidence is not stored: each
analysis keeps the SHA-256 of its inputs, the counts found and who asked. Callers send an API key
whose role decides the permissions in brackets; settings come from SATFX_* variables (see ops.py
and docs/runbook.md).

    python -m satfx serve
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from . import corroborate, db, ops, orbit, sms

settings = ops.load_settings()
ops.setup_logging(settings.log_level)
engine = db.connect(settings.database_url)
_lock = threading.Lock()

app = FastAPI(title="SatFX analysis service", version="1.0.0")
ops.install(app, settings, {"database": lambda: engine.connect().close()})

MAX_ELEMENTS = 5_000_000  # characters: a whole constellation's OMM JSON is well under 1 MB
MAX_EVENTS = 5_000
# Work per request, in satellite positions computed (events x satellites x 30-second steps). About
# 270,000 a second on one core, so this caps a request near half a minute; split larger jobs.
MAX_POSITIONS = 8_000_000


def _budget(events: int, satellites: int, window: int) -> None:
    positions = events * satellites * (4 * window + 1)
    if positions > MAX_POSITIONS:
        raise HTTPException(422, f"{positions:,} satellite positions exceed the {MAX_POSITIONS:,} per request; "
                                 "send fewer events, a narrower window or a smaller constellation")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _log(ident: dict, kind: str, label: str, inputs: Dict[str, str], summary: Dict[str, Any]) -> str:
    aid = uuid.uuid4().hex
    with _lock, engine.begin() as c:
        c.execute(text("INSERT INTO analyses VALUES (:i, :t, :u, :k, :l, :n, :s)"),
                  {"i": aid, "t": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                   "u": ident["user"] or "demo", "k": kind, "l": label, "n": json.dumps(inputs),
                   "s": json.dumps(summary)})
    return aid


@contextmanager
def _file(data: bytes, suffix: str):
    """The submitted bytes as a temporary file (the analysis modules read paths), removed afterwards."""
    fd, path = tempfile.mkstemp(prefix="satfx-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        yield path
    finally:
        os.unlink(path)


def _sats(elements: str):
    with _file(elements.encode(), ".txt") as path:
        try:
            return orbit.load(path), orbit.elements_format(path)
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "elements must be TLE text or an OMM JSON list") from None


def _utc(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("time needs a zone, e.g. 2026-10-09T12:00:00Z")
    return v.astimezone(timezone.utc)


class Place(BaseModel):
    time: datetime
    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    alt_m: float = Field(0.0, ge=-500, le=20_000, allow_inf_nan=False)
    label: str = Field("", max_length=200)

    _zone = field_validator("time")(_utc)


class Geometry(BaseModel):
    elements: str = Field(..., min_length=10, max_length=MAX_ELEMENTS, description="TLE text or OMM JSON list")
    mask: float = Field(10.0, ge=0, le=90, allow_inf_nan=False, description="elevation mask, degrees")
    window: int = Field(15, ge=0, le=120, description="+/- minutes to scan")
    label: str = Field("", max_length=200, description="case or exhibit reference, for the log")


class VisibleRequest(Geometry, Place):
    pass


class CorroborateRequest(Geometry):
    events: List[Place] = Field(..., min_length=1, max_length=MAX_EVENTS)
    format: Literal["json", "csv", "html"] = "json"


@app.post("/v1/visible")
def visible(req: VisibleRequest, ident: dict = Depends(ops.require("analyse"))) -> Dict[str, Any]:
    sats, fmt = _sats(req.elements)
    _budget(1, len(sats), req.window)
    res = orbit.coverage(sats, req.time, req.lat, req.lon, req.alt_m, req.mask, req.window)
    if fmt == "tle":
        res["warning"] = orbit.TLE_WARNING
    inputs = {"elements": _sha(req.elements.encode())}
    summary = {"verdict": res["verdict"], "in_view_now": len(res["in_view_now"]), "satellites": len(sats)}
    ops.DECISIONS.labels(decision=f"visible_{res['verdict']}").inc()
    return {"analysis_id": _log(ident, "visible", req.label, inputs, summary), "inputs": inputs, **res}


@app.post("/v1/corroborate")
def corroborate_events(req: CorroborateRequest, ident: dict = Depends(ops.require("analyse"))) -> Response:
    events = [{"label": e.label or f"event {i + 1}", "time": e.time, "lat": e.lat, "lon": e.lon, "alt_m": e.alt_m}
              for i, e in enumerate(req.events)]
    sats, _ = _sats(req.elements)  # a clear 422 for bad elements before any work
    _budget(len(events), len(sats), req.window)
    with _file(req.elements.encode(), ".txt") as path:
        rep = corroborate.run(events, path, req.mask, req.window)
    rep["assumptions"]["elements_file"] = "(submitted with the request)"
    verdicts: Dict[str, int] = {}
    for row in rep["events"]:
        verdicts[row["verdict"]] = verdicts.get(row["verdict"], 0) + 1
        ops.DECISIONS.labels(decision=f"event_{row['verdict']}").inc()
    inputs = {"elements": rep["assumptions"]["elements_sha256"],
              "events": _sha(json.dumps([e.model_dump(mode="json") for e in req.events], sort_keys=True).encode())}
    aid = _log(ident, "corroborate", req.label, inputs, {"events": len(events), "verdicts": verdicts})
    out = {"json": corroborate.to_json, "csv": corroborate.to_csv, "html": corroborate.to_html}[req.format](rep)
    media = {"json": "application/json", "csv": "text/csv; charset=utf-8", "html": "text/html; charset=utf-8"}[req.format]
    return Response(out, media_type=media, headers={"x-analysis-id": aid})


@app.post("/v1/sms")
async def sms_audit(request: Request, label: str = Query("", max_length=200),
                    ident: dict = Depends(ops.require("analyse"))) -> Dict[str, Any]:
    data = await request.body()
    if not data.startswith(b"SQLite format 3\x00"):
        raise HTTPException(422, "send an iOS sms.db (a SQLite database) as the request body")
    with _file(data, ".db") as path:
        try:
            res = sms.read(path)
        except (ValueError, sqlite3.Error):
            raise HTTPException(422, "not a readable iOS sms.db") from None
    inputs = {"sms_db": _sha(data)}
    unknown = res.get("unrecognised_services", [])
    summary = {"messages": len(res.get("messages", [])), "services": res.get("services", {}),
               "unrecognised_services": unknown}
    if unknown:
        ops.DECISIONS.labels(decision="unusual_transport").inc()
    return {"analysis_id": _log(ident, "sms", label, inputs, summary), "inputs": inputs, **res}


def _row(r) -> Dict[str, Any]:
    d = dict(r)
    for k in ("inputs", "summary"):
        if k in d:
            d[k] = json.loads(d[k])
    return d


@app.get("/v1/analyses", dependencies=[Depends(ops.require("read"))])
def list_analyses(limit: int = Query(50, ge=1, le=1000)) -> Dict[str, Any]:
    with engine.connect() as c:
        rows = c.execute(text("SELECT * FROM analyses ORDER BY created_at DESC LIMIT :n"), {"n": limit}).mappings().all()
    return {"analyses": [_row(r) for r in rows]}


@app.get("/v1/analyses/{analysis_id}", dependencies=[Depends(ops.require("read"))])
def get_analysis(analysis_id: str) -> Dict[str, Any]:
    with engine.connect() as c:
        r = c.execute(text("SELECT * FROM analyses WHERE id = :i"), {"i": analysis_id[:64]}).mappings().first()
    if r is None:
        raise HTTPException(404, "analysis not found")
    return _row(r)
