import sqlite3

from satfx import discover


def _db(path, extra_col=False, rows=(), extra_table=False):
    c = sqlite3.connect(path)
    cols = "ROWID INTEGER PRIMARY KEY, service TEXT, text TEXT" + (", sat_flag INT" if extra_col else "")
    c.execute(f"CREATE TABLE message ({cols})")
    for r in rows:
        c.execute(f"INSERT INTO message VALUES ({','.join('?' * len(r))})", r)
    if extra_table:
        c.execute("CREATE TABLE satellite_session (id INT, started INT)")
        c.execute("INSERT INTO satellite_session VALUES (1, 100)")
    c.commit()
    c.close()


def test_diff_finds_new_schema_and_rows(tmp_path):
    a, b = tmp_path / "e0.db", tmp_path / "e1.db"
    _db(a, rows=[(1, "SMS", "hi"), (2, "SMS", "dup")])
    _db(b, extra_col=True, extra_table=True,
        rows=[(1, "SMS", "hi", 0), (3, "iMessage", "via sat", 1), (4, "iMessage", "via sat", 1)])
    d = discover.diff(str(a), str(b))
    assert "table:satellite_session" in d["schema_added"]
    assert "table:message" in d["schema_changed"]
    assert d["tables"]["satellite_session"] == {"status": "added", "columns": ["id", "started"], "rows": 1}
    m = d["tables"]["message"]
    assert m["columns_added"] == ["sat_flag"]
    assert m["rows_added_total"] == 2 and m["rows_removed_total"] == 1  # duplicates counted, not merged
    assert {"ROWID": 2, "service": "SMS", "text": "dup"} in m["rows_removed"]


def test_diff_identical_is_empty(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    _db(a, rows=[(1, "SMS", "x")])
    _db(b, rows=[(1, "SMS", "x")])
    d = discover.diff(str(a), str(b))
    assert d["tables"] == {} and not d["schema_added"] and not d["schema_changed"]


def test_sweep_encodings_names_and_chunk_boundary(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "a.txt").write_bytes(b"xx Connected to GLOBALSTAR satellite yy")
    (tmp_path / "logs" / "b.bin").write_bytes(b"\x00" * 5 + "Skylo link".encode("utf-16-le"))
    # term split across the 16-byte chunk boundary
    (tmp_path / "logs" / "c.bin").write_bytes(b"A" * 12 + b"Starlink" + b"B" * 30)
    (tmp_path / "stewie_state.plist").write_bytes(b"nothing")
    hits = discover.sweep(str(tmp_path), chunk=16)
    got = {(h["file"].split("\\")[-1].split("/")[-1], h["where"], h["term"], h.get("encoding")) for h in hits}
    assert ("a.txt", "content", "globalstar", "utf-8") in got
    assert ("a.txt", "content", "satellite", "utf-8") in got
    assert ("b.bin", "content", "skylo", "utf-16le") in got
    assert ("c.bin", "content", "starlink", "utf-8") in got
    assert ("stewie_state.plist", "name", "stewie", None) in got
    starlink = [h for h in hits if h["term"] == "starlink" and h["where"] == "content"]
    assert len(starlink) == 1 and starlink[0]["offset"] == 12  # boundary match found once, right offset


def test_sweep_custom_terms_and_cap(tmp_path):
    (tmp_path / "f").write_bytes(b"sos " * 500)
    hits = discover.sweep(str(tmp_path), terms=["SOS"], max_hits_per_file=10)
    assert len(hits) == 10
