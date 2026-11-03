"""Read acquired SQLite evidence, including WAL data, without modifying it."""
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def evidence_connection(path):
    """Read-only connection; a matching `-wal` is read through an isolated working copy.

    Inputs must be an acquired, stable database and its WAL, not a live database being written
    during the copy. No original sidecar is created or checkpointed. URI encoding keeps spaces,
    percent signs and hash marks in file names. `trusted_schema = OFF`: a seized database's views
    and triggers can't call functions.
    """
    source = Path(path).resolve(strict=True)
    wal = source.with_name(source.name + "-wal")
    with tempfile.TemporaryDirectory(prefix="satfx-sqlite-") as directory:
        if wal.is_file():
            database = Path(directory) / "evidence.db"
            shutil.copyfile(source, database)
            shutil.copyfile(wal, database.with_name(database.name + "-wal"))
            options = "?mode=ro"
        else:
            database, options = source, "?mode=ro&immutable=1"
        conn = sqlite3.connect(database.as_uri() + options, uri=True)
        try:
            conn.execute("PRAGMA trusted_schema = OFF")
            yield conn
        finally:
            conn.close()
