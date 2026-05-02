import logging
from typing import Optional, List
from app.core.database import get_connection
from app.core import cache as price_cache

logger = logging.getLogger(__name__)


def upsert_instrument(
    symbol: str,
    name: str = None,
    exchange: str = None,
    currency: str = "INR",
    sector: str = None,
    last_price: float = None
):
    """Save/update instrument master record."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO instrument_master
                (symbol, name, exchange, currency,
                 sector, last_price, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET
                name         = COALESCE(excluded.name, name),
                exchange     = COALESCE(excluded.exchange, exchange),
                sector       = COALESCE(excluded.sector, sector),
                last_price   = COALESCE(excluded.last_price, last_price),
                last_updated = CURRENT_TIMESTAMP
        """, (symbol, name, exchange, currency, sector, last_price))
        conn.commit()
    finally:
        conn.close()


def get_instrument(symbol: str) -> Optional[dict]:
    """Fetch instrument master record."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT * FROM instrument_master WHERE symbol = ?
        """, (symbol,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def search_instruments(query: str, limit: int = 10) -> List[dict]:
    """Search instruments by symbol or name."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT symbol, name, exchange, sector
            FROM instrument_master
            WHERE symbol LIKE ?
               OR name LIKE ?
            ORDER BY symbol
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def sync_prices_to_master(holdings: List[dict]):
    """
    After every upload, sync live prices to instrument_master.
    This builds your reference database over time.
    """
    for h in holdings:
        if h.get("current_price"):
            upsert_instrument(
                symbol=h["symbol"],
                exchange=h.get("exchange"),
                currency=h.get("currency", "INR"),
                sector=h.get("sector"),
                last_price=h.get("current_price"),
            )