"""
Persistent symbol validation cache.
Survives server restarts via diskcache.
Prevents re-validating known-bad symbols.
"""
import logging
from typing import Optional, Tuple
from app.cache.store import _disk, TTL_SYMBOLS

logger = logging.getLogger(__name__)

DELISTED_PREFIX = "delisted:"
VALID_PREFIX    = "valid:"


def is_delisted(symbol: str) -> bool:
    try:
        return bool(_disk.get(f"{DELISTED_PREFIX}{symbol}"))
    except Exception:
        return False


def mark_delisted(symbol: str) -> None:
    try:
        _disk.set(f"{DELISTED_PREFIX}{symbol}", True, expire=TTL_SYMBOLS)
        logger.info(f"🚫 Quarantined delisted: {symbol}")
    except Exception:
        pass


def mark_valid(symbol: str, exchange: str, currency: str) -> None:
    try:
        _disk.set(
            f"{VALID_PREFIX}{symbol}",
            {"exchange": exchange, "currency": currency},
            expire=TTL_SYMBOLS,
        )
    except Exception:
        pass


def get_metadata(symbol: str) -> Optional[dict]:
    try:
        return _disk.get(f"{VALID_PREFIX}{symbol}")
    except Exception:
        return None


def clear_quarantine(symbol: str) -> None:
    """Remove a symbol from quarantine (admin use)."""
    try:
        _disk.delete(f"{DELISTED_PREFIX}{symbol}")
    except Exception:
        pass


def get_exchange(symbol: str) -> str:
    if symbol.endswith(".BO"):
        return "BSE"
    if symbol.endswith(".NS"):
        return "NSE"
    meta = get_metadata(symbol)
    return meta.get("exchange", "NSE") if meta else "NSE"


def get_currency(symbol: str) -> str:
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return "INR"
    meta = get_metadata(symbol)
    return meta.get("currency", "USD") if meta else "USD"


def nse_to_bse(symbol: str) -> str:
    return symbol.replace(".NS", ".BO")


def bse_to_nse(symbol: str) -> str:
    return symbol.replace(".BO", ".NS")