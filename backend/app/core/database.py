import sqlite3
import os
import logging
import threading
from contextlib import contextmanager
from queue import Queue, Empty
from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

_pool: Queue = Queue(maxsize=settings.db_pool_size)
_lock        = threading.Lock()
_initialized = False


def _make_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    conn = sqlite3.connect(
        settings.db_path,
        check_same_thread=False,
        timeout=30,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _init_pool():
    global _initialized
    with _lock:
        if _initialized:
            return
        import os
        os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
        for _ in range(settings.db_pool_size):
            _pool.put(_make_connection())
        _initialized = True
        logger.info(f"DB pool initialized ({settings.db_pool_size} connections)")


@contextmanager
def get_db():
    """Context manager — always returns connection to pool."""
    _init_pool()
    try:
        conn = _pool.get(timeout=5)
    except Empty:
        # Pool exhausted — create temporary connection
        logger.warning("DB pool exhausted — creating temporary connection")
        conn = _make_connection()
        temp = True
    else:
        temp = False

    try:
        yield conn
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        if temp:
            conn.close()
        else:
            _pool.put(conn)


# Backwards-compatible alias
def get_connection() -> sqlite3.Connection:
    """Legacy — prefer get_db() context manager."""
    _init_pool()
    try:
        return _pool.get(timeout=5)
    except Empty:
        return _make_connection()