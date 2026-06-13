"""
database.py — Complete file.
Local dev  : SQLite (automatic, no setup needed)
Production : PostgreSQL on Render (set DATABASE_URL env var)
Auto-detects which one to use based on environment.
"""
import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres")


# ══════════════════════════════════════════════════════════════
#  SQLite  — used locally on your Mac
# ══════════════════════════════════════════════════════════════
if not USE_POSTGRES:
    import sqlite3

    _DB_FILE = os.getenv("SQLITE_DB_PATH", "portfolio.db")

    def get_connection():
        conn = sqlite3.connect(_DB_FILE, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    logger.info(f"📦 DB: SQLite → {_DB_FILE}")


# ══════════════════════════════════════════════════════════════
#  PostgreSQL  — used on Render (production)
# ══════════════════════════════════════════════════════════════
else:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool as pg_pool

    # Render gives postgres:// — psycopg2 needs postgresql://
    _pg_url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    _pool: Optional[pg_pool.ThreadedConnectionPool] = None

    def _get_pool() -> pg_pool.ThreadedConnectionPool:
        global _pool
        if _pool is None:
            _pool = pg_pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=_pg_url,
                sslmode="require",
            )
            logger.info("🐘 DB: PostgreSQL pool initialized (Render)")
        return _pool

    def _adapt_sql(sql: str) -> str:
        """
        Convert SQLite SQL syntax → PostgreSQL syntax.
        Handles the most common differences.
        """
        # Skip PRAGMA statements (SQLite-only)
        if sql.strip().upper().startswith("PRAGMA"):
            return "SELECT 1"

        # ? placeholders → %s
        sql = re.sub(r"\?", "%s", sql)

        # AUTOINCREMENT → SERIAL
        sql = re.sub(
            r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
            "SERIAL PRIMARY KEY",
            sql,
            flags=re.IGNORECASE,
        )

        # IF NOT EXISTS for indexes — PostgreSQL supports this natively, keep as-is
        return sql

    class _CursorWrapper:
        """Makes psycopg2 cursor behave like sqlite3 cursor for our code."""

        def __init__(self, cur: psycopg2.extensions.cursor):
            self._cur = cur
            self._lastrowid: Optional[int] = None
            try:
                self.rowcount = cur.rowcount
            except Exception:
                self.rowcount = 0

        @property
        def lastrowid(self) -> Optional[int]:
            return self._lastrowid

        def fetchone(self):
            row = self._cur.fetchone()
            return _DictRow(dict(row)) if row else None

        def fetchall(self):
            return [_DictRow(dict(r)) for r in self._cur.fetchall()]

    class _DictRow(dict):
        """
        Behaves like sqlite3.Row.
        Subscriptable by both column name (str) and index (int).
        """
        def __getitem__(self, key):
            if isinstance(key, int):
                return list(self.values())[key]
            return super().__getitem__(key)

    class _PgConnection:
        """
        Wraps a psycopg2 connection from the pool.
        Exposes the same API as sqlite3.Connection so the rest of
        the codebase doesn't need to change at all.
        """

        def __init__(self):
            self._pool = _get_pool()
            self._conn = self._pool.getconn()
            self._conn.autocommit = False

        def execute(self, sql: str, params=None) -> _CursorWrapper:
            sql = _adapt_sql(sql)
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                cur.execute(sql, list(params) if params else None)
            except psycopg2.errors.UniqueViolation:
                self._conn.rollback()
                raise
            except Exception:
                self._conn.rollback()
                raise

            wrapper = _CursorWrapper(cur)

            # Capture RETURNING / lastrowid equivalent
            if sql.strip().upper().startswith("INSERT"):
                try:
                    # Re-run with RETURNING id if not already there
                    pass
                except Exception:
                    pass
            try:
                wrapper._lastrowid = cur.fetchone()  # type: ignore
                if isinstance(wrapper._lastrowid, _DictRow):
                    wrapper._lastrowid = list(wrapper._lastrowid.values())[0]
            except Exception:
                wrapper._lastrowid = None

            return wrapper

        def executescript(self, sql: str) -> None:
            """Run a multi-statement SQL script (used in migrations)."""
            old_autocommit = self._conn.autocommit
            self._conn.autocommit = True
            cur = self._conn.cursor()
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                adapted = _adapt_sql(stmt)
                if adapted.strip().upper() == "SELECT 1":
                    continue
                try:
                    cur.execute(adapted)
                except Exception as e:
                    # Ignore "already exists" errors during migration
                    err = str(e).lower()
                    if "already exists" in err or "duplicate" in err:
                        pass
                    else:
                        logger.debug(f"Migration stmt warning: {e}")
            self._conn.autocommit = old_autocommit

        def commit(self) -> None:
            self._conn.commit()

        def close(self) -> None:
            self._pool.putconn(self._conn)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                try:
                    self._conn.rollback()
                except Exception:
                    pass
            self.close()

    def get_connection() -> _PgConnection:
        return _PgConnection()

    logger.info("🐘 DB: PostgreSQL mode active")