"""TEST-ONLY database. Gives the unit tests an isolated in-memory SQL engine with the same schema.
This is NOT an Oracle integration test - see docs/TESTING.md for the live-Oracle procedure."""
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.db import DatabaseUnavailable, Session

sqlite3.register_adapter(Decimal, float)
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda d: d.isoformat(sep=" "))


class SqliteDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
        self.conn.executescript((Path(__file__).parent / "sqlite_schema.sql").read_text())
        self.conn.isolation_level = ""  # deferred transactions: commit/rollback behave like Oracle

    def session(self):
        return Session(self.conn, "sqlite")

    def ping(self):
        return True


class DownDatabase:
    """Simulates an unreachable Oracle instance."""

    def session(self):
        raise DatabaseUnavailable("DPY-6005: cannot connect to database (secret details)")

    def ping(self):
        return False
