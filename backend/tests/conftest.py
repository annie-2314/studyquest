"""Test bootstrap: route all tests to an isolated SQLite file and start fresh
each run. This MUST set DATABASE_URL before any `app.*` import, because
app.config / app.database build the engine at import time."""
import os
import pathlib

os.environ["DATABASE_URL"] = "sqlite:///./test_studyquest.db"
# Force deterministic MOCK mode for tests (empty env var overrides any .env key),
# so the suite never makes real, billable OpenRouter calls.
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["LANGCHAIN_TRACING_V2"] = "false"
# Use the deterministic hash embedding so tests never download the bge model.
os.environ["EMBEDDINGS_MOCK"] = "1"

# Start every test session from a clean database so inserts (e.g. signup) are
# idempotent across repeated runs.
_dbfile = pathlib.Path("test_studyquest.db")
if _dbfile.exists():
    _dbfile.unlink()
