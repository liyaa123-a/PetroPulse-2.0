
"""Database access for Oracle and PostgreSQL."""
from __future__ import annotations

import logging
import re
from typing import Any

from flask import current_app, g

log = logging.getLogger("petropulse")

_BIND_RE = re.compile(r"(?<![:\w]):([A-Za-z][A-Za-z0-9_]*)")


class DatabaseError(Exception):
    pass


class DatabaseUnavailable(DatabaseError):
    pass


class IntegrityConflict(DatabaseError):
    pass


class Session:
    """One connection = one transaction. Committed by the request hook on success."""

    def __init__(self, conn: Any, dialect: str, release=None):
        self.conn, self.dialect, self._release = conn, dialect, release

    def _run(self, cur, sql: str, params: dict | None) -> None:
        params = params or {}
        wanted = set(_BIND_RE.findall(sql))

        if wanted != set(params):
            raise ValueError(
                f"bind mismatch: unused={sorted(set(params) - wanted)} "
                f"missing={sorted(wanted - set(params))}"
            )

        if self.dialect == "postgres":
            sql = _BIND_RE.sub(r"%(\1)s", sql)

        try:
            cur.execute(sql, params)
        except Exception as e:
            name = type(e).__name__
            if "IntegrityError" in name or "UniqueViolation" in name or "ForeignKeyViolation" in name:
                raise IntegrityConflict(str(e)) from e
            if isinstance(e, (ValueError, TypeError)):
                raise
            raise DatabaseError(f"{name}: {e}") from e

    def query(self, sql: str, params: dict | None = None) -> list[dict]:
        cur = self.conn.cursor()
        try:
            self._run(cur, sql, params)
            cols = [c[0].lower() for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            cur.close()

    def one(self, sql: str, params: dict | None = None) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: dict | None = None) -> int:
        cur = self.conn.cursor()
        try:
            self._run(cur, sql, params)
            return cur.rowcount
        finally:
            cur.close()

    def insert(self, sql: str, params: dict) -> int:
        """Insert a row and return its generated ID."""
        cur = self.conn.cursor()
        try:
            if self.dialect == "oracle":
                out = cur.var(int)
                self._run(cur, sql + " RETURNING id INTO :new_id", {**params, "new_id": out})
                return int(out.getvalue()[0])

            if self.dialect == "postgres":
                self._run(cur, sql.rstrip().rstrip(";") + " RETURNING id", params)
                row = cur.fetchone()
                if row is None:
                    raise DatabaseError("Insert did not return a generated ID.")
                return int(row[0])

            self._run(cur, sql, params)
            return int(cur.lastrowid)
        finally:
            cur.close()

    def paginate(self, sql: str, params: dict, page: int, size: int) -> tuple[str, dict]:
        p = {**params, "pg_off": (page - 1) * size, "pg_lim": size}
        if self.dialect == "oracle":
            return sql + " OFFSET :pg_off ROWS FETCH NEXT :pg_lim ROWS ONLY", p
        return sql + " LIMIT :pg_lim OFFSET :pg_off", p

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        try:
            self.conn.rollback()
        except Exception:
            log.exception("rollback failed")

    def close(self) -> None:
        if self._release:
            self._release(self.conn)


class OracleDatabase:
    """Connection pool for Oracle Autonomous Database."""

    def __init__(self, cfg):
        self.cfg, self._pool = cfg, None

    def _get_pool(self):
        if self._pool is None:
            import oracledb

            if not self.cfg.oracle_ready():
                raise DatabaseUnavailable(
                    "Oracle settings (ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN) are not configured"
                )

            oracledb.defaults.fetch_decimals = True
            kwargs: dict[str, Any] = dict(
                user=self.cfg.oracle_user,
                password=self.cfg.oracle_password,
                dsn=self.cfg.oracle_dsn,
                min=1,
                max=self.cfg.pool_max,
                increment=1,
                getmode=oracledb.POOL_GETMODE_WAIT,
                wait_timeout=10000,
                ping_interval=60,
            )

            wallet = self.cfg.resolve_wallet_dir()
            if wallet:
                kwargs.update(config_dir=wallet, wallet_location=wallet)
                if self.cfg.oracle_wallet_password:
                    kwargs["wallet_password"] = self.cfg.oracle_wallet_password

            try:
                self._pool = oracledb.create_pool(**kwargs)
            except Exception as e:
                raise DatabaseUnavailable(f"{type(e).__name__}: {e}") from e

        return self._pool

    def session(self) -> Session:
        pool = self._get_pool()
        try:
            conn = pool.acquire()
        except Exception as e:
            raise DatabaseUnavailable(f"{type(e).__name__}: {e}") from e
        return Session(conn, "oracle", release=pool.release)

    def ping(self) -> bool:
        s = None
        try:
            s = self.session()
            s.query("SELECT 1 AS ok FROM dual")
            return True
        except Exception as e:
            log.error("database ping failed: %s", e)
            return False
        finally:
            if s:
                s.close()


class PostgreSQLDatabase:
    """PostgreSQL connections using the DATABASE_URL environment variable."""

    def __init__(self, cfg):
        self.cfg = cfg

    def session(self) -> Session:
        if not self.cfg.database_url:
            raise DatabaseUnavailable("DATABASE_URL is not configured.")

        try:
            import psycopg

            url = self.cfg.database_url
            if url.startswith("postgres://"):
                url = "postgresql://" + url[len("postgres://"):]

            conn = psycopg.connect(url, connect_timeout=10)
            return Session(conn, "postgres", release=lambda c: c.close())
        except DatabaseUnavailable:
            raise
        except Exception as e:
            raise DatabaseUnavailable(f"{type(e).__name__}: {e}") from e

    def ping(self) -> bool:
        s = None
        try:
            s = self.session()
            s.query("SELECT 1 AS ok")
            return True
        except Exception as e:
            log.error("database ping failed: %s", e)
            return False
        finally:
            if s:
                s.close()


def get_session() -> Session:
    if "db_session" not in g:
        g.db_session = current_app.extensions["pp_database"].session()
    return g.db_session


def init_db_hooks(app, database) -> None:
    app.extensions["pp_database"] = database

    @app.after_request
    def finish_transaction(resp):
        s = g.get("db_session")
        if s is not None:
            if resp.status_code < 400:
                try:
                    s.commit()
                except Exception as e:
                    log.error("commit failed: %s", e)
                    s.rollback()
                    from flask import jsonify
                    return jsonify({
                        "error": {
                            "code": "DATABASE_ERROR",
                            "message": "A database error occurred.",
                        }
                    }), 500
            else:
                s.rollback()
        return resp

    @app.teardown_appcontext
    def close_session(_exc):
        s = g.pop("db_session", None)
        if s is not None:
            s.rollback()
            s.close()
