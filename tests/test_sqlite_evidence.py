import sqlite3

import pytest

from satfx import discover, sms


@pytest.mark.parametrize('filename', ['sms.db', 'sms #1%.db'])
def test_wal_messages_are_read_without_changing_evidence(tmp_path, filename):
    path = tmp_path / filename
    writer = sqlite3.connect(path)
    try:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT, service TEXT, date INT)')
        writer.commit()
        writer.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        writer.execute("INSERT INTO message VALUES (1, 'wal-message', 'latest message', 'SMS', 781000000)")
        writer.commit()
        evidence = {p: p.read_bytes() for p in tmp_path.iterdir()}
        result = sms.read(str(path))
        assert result['messages'][0]['guid'] == 'wal-message'
        snapshot = discover.snapshot(str(path))
        assert sum(snapshot['tables']['message']['rows'].values()) == 1
        assert {p: p.read_bytes() for p in tmp_path.iterdir()} == evidence
    finally:
        writer.close()


def test_database_without_wal_supports_uri_characters(tmp_path):
    path = tmp_path / 'sms #1%.db'
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE message (ROWID INTEGER PRIMARY KEY, text TEXT)')
    connection.execute("INSERT INTO message VALUES (1, 'saved message')")
    connection.commit()
    connection.close()
    original = path.read_bytes()
    assert sms.read(str(path))['messages'][0]['text'] == 'saved message'
    assert path.read_bytes() == original
