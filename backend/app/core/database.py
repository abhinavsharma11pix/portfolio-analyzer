import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "portfolio.db"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_db():
    """Dependency for FastAPI routes."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()