import plistlib
import sqlite3

from satfx import sms


def typedstream(text: str, gap: bytes = b"\x01\x94\x84\x01") -> bytes:
    """Minimal NSAttributedString-like blob with the documented string layout."""
    raw = text.encode()
    if len(raw) < 0x80:
        ln = bytes([len(raw)])
    elif len(raw) < 0x10000:
        ln = b"\x81" + len(raw).to_bytes(2, "little")
    else:
        ln = b"\x82" + len(raw).to_bytes(4, "little")
    # a class-name NSString first (no inline string), then the real one
    return b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject" \
           b"\x00\x85\x92\x84\x84\x84\x08NSString" + gap + b"\x2b" + ln + raw + b"\x86\x84\x02iI\x01"


def make_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT);
        CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, chat_identifier TEXT);
        CREATE TABLE chat_message_join (chat_id INT, message_id INT);
        CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT, attributedBody BLOB,
            service TEXT, date INT, date_delivered INT, date_read INT, is_from_me INT, handle_id INT,
            destination_caller_id TEXT, message_summary_info BLOB);
        INSERT INTO handle VALUES (1, '+15555550123', 'iMessage');
        INSERT INTO chat VALUES (1, '+15555550123');
    """)
    ns = 781_000_000 * 10**9  # 2025-10-01 in Apple-epoch nanoseconds
    rows = [
        (1, "g1", "plain sms", None, "SMS", ns, 0, 0, 0, 1, None, None),
        (2, "g2", None, typedstream("from attributedBody"), "iMessage", ns + 10**9, 0, 0, 1, 1, "+15555550100",
         plistlib.dumps({"ust": True, "ec": {}}, fmt=plistlib.FMT_BINARY)),
        (3, "g3", None, typedstream("x" * 300), "RCS", ns + 2 * 10**9, 0, 0, 0, 1, None, b"not a plist"),
        (4, "g4", "odd transport", None, "SyntheticSat", ns + 3 * 10**9, 0, 0, 1, 1, None, None),
        (5, "g5", None, b"\x00junk", None, 781_000_010, 0, 0, 0, 1, None, None),  # seconds-era date, no service
    ]
    c.executemany("INSERT INTO message VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    c.executemany("INSERT INTO chat_message_join VALUES (1, ?)", [(r[0],) for r in rows])
    c.commit()
    c.close()


def test_attributed_text_layouts():
    assert sms.attributed_text(typedstream("hello")) == "hello"
    assert sms.attributed_text(typedstream("é" * 100)) == "é" * 100          # 0x81 two-byte length
    assert sms.attributed_text(typedstream("hi", gap=b"\x01\x95\x84\x01\x00")) == "hi"  # gap varies
    assert sms.attributed_text(b"no marker here") is None
    assert sms.attributed_text(b"NSString\x01\x2b\x05ab") is None           # truncated: never throws
    assert sms.attributed_text(None) is None
    assert sms.attributed_text(typedstream("z" * 70000)) == "z" * 70000       # 0x82 four-byte length
    decoy = bytes([0x84, 0x84]) + b"NSString" + bytes(10) + typedstream("real")
    assert sms.attributed_text(decoy) == "real"                             # skip class-name occurrence


def test_apple_time():
    assert sms.apple_time(0) is None
    assert sms.apple_time(781_000_000 * 10**9) == sms.apple_time(781_000_000)  # ns and s eras agree
    assert sms.apple_time(781_000_000).startswith("2025-")


def test_read_audits_transport(tmp_path):
    db = tmp_path / "sms.db"
    make_db(str(db))
    r = sms.read(str(db))
    by = {m["guid"]: m for m in r["messages"]}
    assert r["services"] == {"SMS": 1, "iMessage": 1, "RCS": 1, "SyntheticSat": 1, "<blank>": 1}
    assert r["unrecognised_services"] == ["SyntheticSat"]
    assert by["g4"]["service_flag"] == "unrecognised" and by["g1"]["service_flag"] is None
    assert by["g2"]["text"] == "from attributedBody" and by["g2"]["text_source"] == "attributedBody"
    assert by["g3"]["text"] == "x" * 300
    assert by["g5"]["text"] is None and by["g5"]["text_source"] == "undecoded"
    assert by["g2"]["summary_info_keys"] == ["ec", "ust"] and by["g3"]["summary_info_keys"] == ["<undecodable>"]
    assert by["g2"]["handle"] == "+15555550123" and by["g2"]["chat"] == "+15555550123"
    assert by["g2"]["from_me"] and by["g2"]["own_address"] == "+15555550100"
    # g5's raw date is in seconds (small number) but it is the latest message in real time
    assert [m["guid"] for m in r["messages"]] == ["g1", "g2", "g3", "g4", "g5"]
