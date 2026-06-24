"""Test bootstrap: route all tests to an isolated SQLite file and start fresh
each run. This MUST set DATABASE_URL before any `app.*` import, because
app.config / app.database build the engine at import time."""
import os
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test_studyquest.db"

# Start every test session from a clean database so inserts (e.g. signup) are
# idempotent across repeated runs.
_dbfile = pathlib.Path("test_studyquest.db")
if _dbfile.exists():
    _dbfile.unlink()
