"""Verify the Oracle connection and schema. Run from the backend folder with your ORACLE_* variables set:

    python scripts/check_oracle.py

Prints what it checked; exits non-zero on failure. Never prints the password."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config  # noqa: E402
from app.db import OracleDatabase  # noqa: E402

TABLES = {"PP_USERS", "PP_WELLS", "PP_PRODUCTION", "PP_TARGETS", "PP_ALERTS"}

cfg = Config()
print(f"User: {cfg.oracle_user or '(not set)'} | DSN: {cfg.oracle_dsn or '(not set)'} | wallet: {'yes' if (cfg.oracle_wallet_dir or cfg.oracle_wallet_b64) else 'no'}")
db = OracleDatabase(cfg)
try:
    s = db.session()
except Exception as e:  # noqa: BLE001
    sys.exit(f"FAILED to connect: {e}")
try:
    print("Connected as:", s.one("SELECT USER AS u FROM dual")["u"])
    have = {r["table_name"] for r in s.query("SELECT table_name FROM user_tables")}
    missing = TABLES - have
    print("Tables present:", ", ".join(sorted(TABLES & have)) or "none")
    if missing:
        sys.exit(f"MISSING tables: {', '.join(sorted(missing))} - run sql/oracle/01_schema.sql and 02_constraints_indexes.sql")
    print("Row counts:", {t: s.one(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in sorted(TABLES)})
    print("OK - Oracle connection and schema verified.")
finally:
    s.close()
