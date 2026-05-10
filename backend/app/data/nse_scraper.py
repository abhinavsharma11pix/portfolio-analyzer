"""
NSE scraper with persistent session (not recreated per call).
"""
import logging
import threading
import requests
from typing import Optional

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.nseindia.com/",
}

_session:      Optional[requests.Session] = None
_session_lock  = threading.Lock()
_session_ts    = 0.0
SESSION_TTL    = 300  # refresh session every 5 minutes


def _get_session() -> requests.Session:
    """Returns a persistent session, refreshed periodically."""
    global _session, _session_ts
    import time

    with _session_lock:
        if _session is None or (time.time() - _session_ts) > SESSION_TTL:
            s = requests.Session()
            try:
                s.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=4)
            except Exception:
                pass
            _session    = s
            _session_ts = time.time()
        return _session


def fetch_nse_price(symbol: str) -> Optional[float]:
    clean = symbol.replace(".NS", "").replace(".BO", "").upper()
    try:
        session = _get_session()
        url     = f"https://www.nseindia.com/api/quote-equity?symbol={clean}"
        res     = session.get(url, headers=NSE_HEADERS, timeout=6)
        if res.status_code == 200:
            data  = res.json()
            price = (
                data.get("priceInfo", {}).get("lastPrice") or
                data.get("priceInfo", {}).get("close")
            )
            if price:
                return float(price)
    except Exception as e:
        logger.debug(f"NSE fetch failed {clean}: {e}")
    return None