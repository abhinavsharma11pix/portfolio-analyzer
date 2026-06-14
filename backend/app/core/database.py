"""
database.py — Complete file.
Pure SQLite. No external database service required.
Identical behaviour locally and on Render — zero configuration.

WHY SQLITE FOR A RESUME/PORTFOLIO PROJECT:
  - No external service to expire, sleep, pause, or refuse connections
  - File lives on Render's local disk for the container's lifetime
  - Resets only on redeploy (rare) — acceptable because auth/saved
    portfolios/alerts are optional extras, not the core product
  - The core analyzer (upload -> analytics -> AI advisor -> PDF) is
    fully stateless and works regardless of DB state
"""
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_FILE = os.getenv("SQLITE_DB_PATH", "portfolio.db")


def get_connection() -> sqlite3.Connection:
    """Get a new SQLite connection. Caller is responsible for closing it."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


logger.info(f"📦 DB: SQLite -> {DB_FILE}")
