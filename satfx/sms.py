"""iOS sms.db reader that audits the transport of every message (research/01, 03).

`message.service` is reported verbatim and anything other than iMessage/SMS/RCS is flagged, since
no satellite value is documented yet and Apple added RCS as recently as iOS 18. Text comes from
`text`, else from `attributedBody` (typedstream; layout per ChatExportKnowledge/attributedBody.md).
Original evidence is never written. Acquire sms.db with its matching -wal first;
WAL data is read through an isolated working copy so the newest rows are included.
"""
import plistlib
from datetime import datetime, timedelta, timezone

from satfx._sqlite import evidence_connection

KNOWN_SERVICES = {"iMessage", "SMS", "RCS"}
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


def apple_time(v):
    """sms.db dates: seconds since 2001-01-01 (old), or nanoseconds (iOS 11+). 0/None -> None."""
    if not v:
        return None
    secs = v / 1e9 if abs(v) > 1e11 else v
    return (APPLE_EPOCH + timedelta(seconds=secs)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def attributed_text(blob: bytes | None) -> str | None:
    """Message string from an NSAttributedString typedstream blob; None if not decodable."""
    if not blob:
        return None
    start = 0
    while (i := blob.find(b"NSString", start)) != -1:
        start = i + 8
        tag = blob.find(b"\x2b", start, start + 8)
        if tag == -1:
            continue
        p = tag + 1
        if p >= len(blob):
            continue
        n = blob[p]
        if n == 0x81:
            n, p = int.from_bytes(blob[p + 1:p + 3], "little"), p + 3
        elif n == 0x82:
            n, p = int.from_bytes(blob[p + 1:p + 5], "little"), p + 5
        else:
            p += 1
        raw = blob[p:p + n]
        if len(raw) != n:
            continue
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "�" not in s:
            return s
    return None


def _summary_keys(blob):
    if not blob:
        return None
    try:
        d = plistlib.loads(blob)
    except Exception:
        return ["<undecodable>"]
    return sorted(map(str, d)) if isinstance(d, dict) else [type(d).__name__]


def read(path: str) -> dict:
    with evidence_connection(path) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(message)")}
        if not cols:
            raise ValueError(f"{path}: no 'message' table; not an iOS sms.db")
        want = [c for c in ("ROWID", "guid", "text", "attributedBody", "service", "date", "date_delivered",
                            "date_read", "is_from_me", "handle_id", "destination_caller_id",
                            "message_summary_info") if c in cols]
        handles = dict(conn.execute("SELECT ROWID, id FROM handle")) if _has(conn, "handle") else {}
        chats = {}
        if _has(conn, "chat") and _has(conn, "chat_message_join"):
            chats = dict(conn.execute("SELECT j.message_id, c.chat_identifier FROM chat_message_join j "
                                      "JOIN chat c ON c.ROWID = j.chat_id"))
        msgs, services = [], {}
        for row in conn.execute(f"SELECT {', '.join(want)} FROM message ORDER BY ROWID"):
            m = dict(zip(want, row))
            svc = m.get("service")
            key = svc if svc else "<blank>"
            services[key] = services.get(key, 0) + 1
            text, src = m.get("text"), "text"
            if not text:
                text = attributed_text(m.get("attributedBody"))
                src = "attributedBody" if text else ("undecoded" if m.get("attributedBody") else "none")
            msgs.append({
                "rowid": m.get("ROWID"), "guid": m.get("guid"),
                "time_utc": apple_time(m.get("date")), "delivered_utc": apple_time(m.get("date_delivered")),
                "read_utc": apple_time(m.get("date_read")),
                "service": svc,
                "service_flag": None if not svc or svc in KNOWN_SERVICES else "unrecognised",
                "from_me": bool(m.get("is_from_me")), "handle": handles.get(m.get("handle_id")),
                "chat": chats.get(m.get("ROWID")), "own_address": m.get("destination_caller_id"),
                "text": text, "text_source": src,
                "summary_info_keys": _summary_keys(m.get("message_summary_info")),
            })
        # Sort on decoded time: one database can mix seconds-era and nanosecond-era raw values.
        msgs.sort(key=lambda m: (m["time_utc"] is None, m["time_utc"] or ""))
        return {"messages": msgs, "services": services,
                "unrecognised_services": sorted(k for k in services if k != "<blank>" and k not in KNOWN_SERVICES)}


def _has(conn, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
