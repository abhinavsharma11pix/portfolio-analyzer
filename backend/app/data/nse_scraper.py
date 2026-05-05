import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

NSE_BASE  = "https://www.nseindia.com"
NSE_QUOTE = "https://www.nseindia.com/api/quote-equity?symbol={}"
NSE_MARKET_STATUS = "https://www.nseindia.com/api/marketStatus"


def _get_session() -> requests.Session:
    """NSE requires cookie from homepage first."""
    session = requests.Session()
    try:
        session.get(
            NSE_BASE, headers=NSE_HEADERS, timeout=5
        )
    except Exception:
        pass
    return session


def fetch_nse_price(symbol: str) -> Optional[float]:
    """
    Fetch live price from NSE India.
    Returns None if unavailable — caller falls back to yfinance.
    """
    clean = symbol.replace(".NS", "").replace(".BO", "").upper()
    try:
        session = _get_session()
        url = NSE_QUOTE.format(clean)
        res = session.get(url, headers=NSE_HEADERS, timeout=8)
        if res.status_code == 200:
            data  = res.json()
            price = (
                data.get("priceInfo", {}).get("lastPrice") or
                data.get("priceInfo", {}).get("close")
            )
            if price:
                logger.debug(f"NSE ✅ {clean}: ₹{price}")
                return float(price)
    except Exception as e:
        logger.debug(f"NSE ❌ {clean}: {e}")
    return None


def fetch_nse_market_status() -> dict:
    """Fetch official NSE market open/close status."""
    try:
        session = _get_session()
        res = session.get(
            NSE_MARKET_STATUS, headers=NSE_HEADERS, timeout=5
        )
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}