import time
import logging
from typing import Any, Optional
from app.db.repositories import PriceCacheRepository

logger = logging.getLogger(__name__)

# L1: In-memory cache
_memory_store: dict = {}
_memory_ttl: dict = {}

price_repo = PriceCacheRepository()


def get_cache_ttl() -> int:
    """Smart TTL based on market hours (IST)."""
    from datetime import datetime
    import pytz
    now = datetime.now(tz=pytz.timezone("Asia/Kolkata"))
    if now.weekday() >= 5:
        return 21600   # Weekend: 6 hours
    if 9 <= now.hour < 16:
        return 300     # Market hours: 5 min
    return 1800        # After hours: 30 min


def get_memory(key: str) -> Optional[Any]:
    """L1: In-memory cache get."""
    if key in _memory_store:
        if time.time() < _memory_ttl.get(key, 0):
            return _memory_store[key]
        del _memory_store[key]
        _memory_ttl.pop(key, None)
    return None


def set_memory(key: str, value: Any, ttl: int = 300):
    """L1: In-memory cache set."""
    _memory_store[key] = value
    _memory_ttl[key] = time.time() + ttl


def get_price(symbol: str) -> Optional[float]:
    """
    3-tier price cache:
    L1 memory → L2 SQLite → None (fetch fresh)
    """
    # L1: memory
    val = get_memory(f"price:{symbol}")
    if val is not None:
        return val

    # L2: SQLite
    ttl = get_cache_ttl()
    val = price_repo.get_price(symbol, max_age_seconds=ttl)
    if val is not None:
        set_memory(f"price:{symbol}", val, ttl=60)
        return val

    return None


def set_price(symbol: str, price: float,
              currency: str = "INR",
              change_pct: float = None):
    """Save price to both L1 and L2."""
    ttl = get_cache_ttl()
    set_memory(f"price:{symbol}", price, ttl=60)
    price_repo.set_price(
        symbol, price, currency, change_pct
    )


def invalidate(key: str):
    """Remove from memory cache."""
    _memory_store.pop(key, None)
    _memory_ttl.pop(key, None)


def clear_all():
    """Clear entire memory cache."""
    _memory_store.clear()
    _memory_ttl.clear()