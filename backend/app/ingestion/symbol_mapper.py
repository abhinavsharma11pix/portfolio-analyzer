import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Common name → NSE symbol mappings
NAME_TO_SYMBOL = {
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "tata consultancy": "TCS.NS",
    "tata consultancy services": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "hdfc": "HDFCBANK.NS",
    "wipro": "WIPRO.NS",
    "tata motors": "TATAMOTORS.NS",
    "tatamotors": "TATAMOTORS.NS",
    "itc": "ITC.NS",
    "sbi": "SBIN.NS",
    "state bank": "SBIN.NS",
    "state bank of india": "SBIN.NS",
    "axis bank": "AXISBANK.NS",
    "axisbank": "AXISBANK.NS",
    "kotak": "KOTAKBANK.NS",
    "kotak mahindra": "KOTAKBANK.NS",
    "kotakbank": "KOTAKBANK.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "bajfinance": "BAJFINANCE.NS",
    "maruti": "MARUTI.NS",
    "maruti suzuki": "MARUTI.NS",
    "asian paints": "ASIANPAINT.NS",
    "asianpaint": "ASIANPAINT.NS",
    "hul": "HINDUNILVR.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "hindunilvr": "HINDUNILVR.NS",
    "sun pharma": "SUNPHARMA.NS",
    "sunpharma": "SUNPHARMA.NS",
    "dr reddy": "DRREDDY.NS",
    "drreddy": "DRREDDY.NS",
    "cipla": "CIPLA.NS",
    "ultracemco": "ULTRACEMCO.NS",
    "ultratech": "ULTRACEMCO.NS",
    "ongc": "ONGC.NS",
    "ntpc": "NTPC.NS",
    "powergrid": "POWERGRID.NS",
    "titan": "TITAN.NS",
    "nestleindia": "NESTLEIND.NS",
    "nestle india": "NESTLEIND.NS",
    "apple": "AAPL",
    "aapl": "AAPL",
    "google": "GOOGL",
    "googl": "GOOGL",
    "alphabet": "GOOGL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "amazon": "AMZN",
    "amzn": "AMZN",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "nvda": "NVDA",
}

# Known US stocks (no suffix needed)
US_STOCKS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "META", "NVDA", "NFLX", "UBER", "LYFT",
    "PYPL", "SQ", "SHOP", "ZOOM", "SNAP",
    "TWTR", "SPOT", "COIN", "HOOD", "RBLX",
}


def resolve_symbol(raw: str) -> Optional[str]:
    """
    Convert any ticker format to yfinance-compatible symbol.

    Examples:
        "RELIANCE"     → "RELIANCE.NS"
        "reliance"     → "RELIANCE.NS"
        "AAPL"         → "AAPL"
        "HDFC BANK"    → "HDFCBANK.NS"
        "RELIANCE.NS"  → "RELIANCE.NS" (already correct)
        "RELIANCE-EQ"  → "RELIANCE.NS" (Zerodha format)
    """
    if not raw:
        return None

    cleaned = raw.strip()

    # Already has exchange suffix
    if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
        return cleaned.upper()

    # US stock — no suffix
    upper = cleaned.upper()
    if upper in US_STOCKS:
        return upper

    # Try name mapping
    lower = cleaned.lower()
    if lower in NAME_TO_SYMBOL:
        return NAME_TO_SYMBOL[lower]

    # Zerodha format: "RELIANCE-EQ" → "RELIANCE.NS"
    if "-EQ" in upper:
        base = upper.replace("-EQ", "")
        return f"{base}.NS"

    # BSE format: "500325" (numeric = BSE code, skip)
    if cleaned.isdigit():
        logger.warning(f"Skipping BSE code (not supported): {cleaned}")
        return None

    # Default: assume NSE
    return f"{upper}.NS"


def detect_exchange(symbol: str) -> str:
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    if symbol in US_STOCKS or not "." in symbol:
        return "US"
    return "NSE"


def detect_currency(symbol: str) -> str:
    exchange = detect_exchange(symbol)
    return "USD" if exchange == "US" else "INR"