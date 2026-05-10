import time
import logging
import threading
from typing import Optional, Dict, Tuple
from app.core.market_calendar import get_refresh_interval

logger = logging.getLogger(__name__)

# In-memory L1 cache: {symbol: (price, currency, timestamp)}
_cache: Dict[str, Tuple[float, str, float]] = {}
_lock  = threading.RLock()


def get_price(symbol: str) -> Optional[float]:
    with _lock:
        entry = _cache.get(symbol)
        if not entry:
            return None
        price, _, ts = entry
        ttl = get_refresh_interval(has_active_connections=True)
        if time.time() - ts > ttl:
            del _cache[symbol]
            return None
        return price


def set_price(symbol: str, price: float, currency: str = "INR") -> None:
    if not price or price <= 0:
        return
    with _lock:
        _cache[symbol] = (float(price), currency, time.time())


def get_many(symbols: list) -> Dict[str, Optional[float]]:
    return {s: get_price(s) for s in symbols}


def invalidate(symbol: str) -> None:
    with _lock:
        _cache.pop(symbol, None)


def clear_all() -> None:
    with _lock:
        _cache.clear()


def cache_stats() -> Dict:
    with _lock:
        return {
            "size":    len(_cache),
            "symbols": list(_cache.keys()),
        }