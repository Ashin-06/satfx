"""Read acquired SQLite evidence, including WAL data, without modifying it."""
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def evidence_connection(path):
    """Use an isolated working copy when WAL recovery may need a shared-memory file.

    Inputs must be an acquired, stable database and its matching WAL, not a live
    database being written during the copy. No original sidecar is created or
    checkpointed. URI encoding preserves spaces, percent signs, and hash marks.
    """
    source = Path(path).resolve(strict=True)
    wal = source.with_name(source.name + '-wal')
    with tempfile.TemporaryDirectory(prefix='satfx-sqlite-') as directory:
        if wal.is_file():
            database = Path(directory) / 'evidence.db'
            shutil.copyfile(source, database)
            shutil.copyfile(wal, database.with_name(database.name + '-wal'))
            options = '?mode=ro'
        else:
            database = source
            options = '?mode=ro&immutable=1'
        connection = sqlite3.connect(database.as_uri() + options, uri=True)
        try:
            yield connection
        finally:
            connection.close()
