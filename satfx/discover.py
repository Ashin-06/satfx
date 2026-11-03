"""Artifact discovery for the lab protocol (research/03): SQLite before/after diff and a term sweep."""
import os
import sqlite3
from collections import Counter

# Terms worth sweeping for after a satellite session. "stewie": Apple's reported project codename.
DEFAULT_TERMS = ["satellite", "globalstar", "skylo", "starlink", "iridium", "stewie", "emergency sos",
                 "t-satellite", "inreach", "garmin response"]


def _val(v):
    return v.hex() if isinstance(v, (bytes, bytearray)) else v


def snapshot(path: str) -> dict:
    """{"schema": {name: sql}, "tables": {table: {"columns": [...], "rows": Counter}}}, read-only."""
    conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        schema = {f"{t}:{n}": sql for t, n, sql in conn.execute("SELECT type, name, sql FROM sqlite_master")}
        tables = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            ident = '"' + name.replace('"', '""') + '"'  # names come from the evidence file: quote them properly
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({ident})")]  # nosec B608 - quoted identifier
            rows = Counter(tuple(_val(v) for v in r) for r in conn.execute(f"SELECT * FROM {ident}"))  # nosec B608
            tables[name] = {"columns": cols, "rows": rows}
        return {"schema": schema, "tables": tables}
    finally:
        conn.close()


def diff(before: str, after: str, max_rows: int = 200) -> dict:
    """What changed between two snapshots of one database. Rows compare on shared columns."""
    a, b = snapshot(before), snapshot(after)
    out = {
        "schema_added": {k: v for k, v in b["schema"].items() if k not in a["schema"]},
        "schema_removed": sorted(k for k in a["schema"] if k not in b["schema"]),
        "schema_changed": sorted(k for k in a["schema"] if k in b["schema"] and a["schema"][k] != b["schema"][k]),
        "tables": {},
    }
    for t in sorted(set(a["tables"]) | set(b["tables"])):
        ta, tb = a["tables"].get(t), b["tables"].get(t)
        if not ta or not tb:
            only = tb or ta
            out["tables"][t] = {"status": "added" if tb else "removed", "columns": only["columns"],
                                "rows": sum(only["rows"].values())}
            continue
        shared = [c for c in tb["columns"] if c in ta["columns"]]
        ia, ib = [ta["columns"].index(c) for c in shared], [tb["columns"].index(c) for c in shared]
        ra = Counter({tuple(r[i] for i in ia): n for r, n in ta["rows"].items()})
        rb = Counter({tuple(r[i] for i in ib): n for r, n in tb["rows"].items()})
        added, removed = rb - ra, ra - rb
        cols_added = [c for c in tb["columns"] if c not in ta["columns"]]
        cols_removed = [c for c in ta["columns"] if c not in tb["columns"]]
        if added or removed or cols_added or cols_removed:
            out["tables"][t] = {
                "status": "changed", "columns_added": cols_added, "columns_removed": cols_removed,
                "rows_before": sum(ta["rows"].values()), "rows_after": sum(tb["rows"].values()),
                "rows_added": [dict(zip(shared, r)) for r in list(added.elements())[:max_rows]],
                "rows_removed": [dict(zip(shared, r)) for r in list(removed.elements())[:max_rows]],
                "rows_added_total": sum(added.values()), "rows_removed_total": sum(removed.values()),
            }
    return out


def _printable(b: bytes) -> str:
    return "".join(chr(c) if 32 <= c < 127 else "." for c in b)


def sweep(root: str, terms=None, chunk: int = 8 << 20, max_hits_per_file: int = 50) -> list[dict]:
    """Case-insensitive search for terms in file names and contents (UTF-8 and UTF-16LE).

    Compressed containers (e.g. unified-log .tracev3) will not match; decompress or parse them first.
    """
    terms = [t.lower() for t in (terms or DEFAULT_TERMS)]
    needles = [(t, "utf-8", t.encode()) for t in terms] + [(t, "utf-16le", t.encode("utf-16-le")) for t in terms]
    overlap = max(len(n) for _, _, n in needles) - 1
    hits = []
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            if os.path.islink(path):
                continue
            hits += [{"file": path, "where": "name", "term": t} for t in terms if t in path.lower()]
            found, seen = [], set()
            try:
                fh = open(path, "rb")
            except OSError as e:  # unreadable file: report it, keep sweeping
                hits.append({"file": path, "where": "error", "error": f"{type(e).__name__}: {e}"})
                continue
            with fh:
                base, tail = 0, b""
                while len(found) < max_hits_per_file and (block := fh.read(chunk)):
                    data = (tail + block).lower()
                    start = base - len(tail)
                    for term, enc, needle in needles:
                        i = data.find(needle)
                        while i != -1 and len(found) < max_hits_per_file:
                            off = start + i
                            if (off, enc, term) not in seen:
                                seen.add((off, enc, term))
                                ctx = (tail + block)[max(0, i - 40):i + len(needle) + 40]
                                found.append({"file": path, "where": "content", "term": term, "encoding": enc,
                                              "offset": off, "context": _printable(ctx.replace(b"\x00", b""))})
                            i = data.find(needle, i + 1)
                    tail = block[-overlap:] if overlap else b""
                    base += len(block)
            hits += sorted(found, key=lambda h: h["offset"])
    return hits
