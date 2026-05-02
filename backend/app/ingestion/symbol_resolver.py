import logging
from typing import Optional, Tuple
from app.core.database import get_connection

logger = logging.getLogger(__name__)

# Layer 1: Static map (top 100 Indian + US stocks)
STATIC_MAP = {
    # Indian stocks
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "INFOSYS": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "HDFC": "HDFCBANK.NS",
    "WIPRO": "WIPRO.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "ITC": "ITC.NS",
    "SBIN": "SBIN.NS",
    "SBI": "SBIN.NS",
    "STATE BANK": "SBIN.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "AXISBANK": "AXISBANK.NS",
    "AXIS BANK": "AXISBANK.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "KOTAK": "KOTAKBANK.NS",
    "KOTAK MAHINDRA": "KOTAKBANK.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "MARUTI": "MARUTI.NS",
    "MARUTI SUZUKI": "MARUTI.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "ASIAN PAINTS": "ASIANPAINT.NS",
    "HUL": "HINDUNILVR.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "DRREDDY": "DRREDDY.NS",
    "DR REDDY": "DRREDDY.NS",
    "CIPLA": "CIPLA.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "ULTRATECH": "ULTRACEMCO.NS",
    "ONGC": "ONGC.NS",
    "NTPC": "NTPC.NS",
    "POWERGRID": "POWERGRID.NS",
    "TITAN": "TITAN.NS",
    "NESTLEIND": "NESTLEIND.NS",
    "NESTLE INDIA": "NESTLEIND.NS",
    "LTIM": "LTIM.NS",
    "LTI": "LTIM.NS",
    "LT": "LT.NS",
    "LARSEN": "LT.NS",
    "LARSEN AND TOUBRO": "LT.NS",
    "ADANIPORTS": "ADANIPORTS.NS",
    "ADANI PORTS": "ADANIPORTS.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "BAJAJ FINSERV": "BAJAJFINSV.NS",
    "BRITANNIA": "BRITANNIA.NS",
    "DIVISLAB": "DIVISLAB.NS",
    "EICHERMOT": "EICHERMOT.NS",
    "EICHER": "EICHERMOT.NS",
    "GRASIM": "GRASIM.NS",
    "HCLTECH": "HCLTECH.NS",
    "HCL TECH": "HCLTECH.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",
    "HERO MOTO": "HEROMOTOCO.NS",
    "HINDALCO": "HINDALCO.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "INDUSIND": "INDUSINDBK.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "JSW STEEL": "JSWSTEEL.NS",
    "M&M": "M&M.NS",
    "MAHINDRA": "M&M.NS",
    "SBILIFE": "SBILIFE.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "TATA STEEL": "TATASTEEL.NS",
    "TECHM": "TECHM.NS",
    "TECH MAHINDRA": "TECHM.NS",
    "UPL": "UPL.NS",
    "ZOMATO": "ZOMATO.NS",
    "NYKAA": "NYKAA.NS",
    "PAYTM": "PAYTM.NS",
    # US stocks
    "AAPL": "AAPL",
    "APPLE": "AAPL",
    "GOOGL": "GOOGL",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "MSFT": "MSFT",
    "MICROSOFT": "MSFT",
    "AMZN": "AMZN",
    "AMAZON": "AMZN",
    "TSLA": "TSLA",
    "TESLA": "TSLA",
    "META": "META",
    "FACEBOOK": "META",
    "NVDA": "NVDA",
    "NVIDIA": "NVDA",
    "NFLX": "NFLX",
    "NETFLIX": "NFLX",
    "UBER": "UBER",
    "PYPL": "PYPL",
    "PAYPAL": "PYPL",
}

US_STOCKS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "META", "NVDA", "NFLX", "UBER", "PYPL",
    "SQ", "SHOP", "ZOOM", "SNAP", "COIN",
    "RBLX", "HOOD", "SPOT", "AMD", "INTC",
    "BABA", "JD", "NIO", "XPEV", "LI",
}


class SmartSymbolResolver:
    """
    Multi-layer symbol resolver with confidence scoring.

    Layer 1: Already resolved (.NS / .BO suffix)  → 1.0
    Layer 2: DB alias cache (learned over time)    → cached confidence
    Layer 3: Static map (top stocks)               → 0.95
    Layer 4: Fuzzy match (rapidfuzz)               → 0.7-0.9
    Layer 5: yfinance search (API fallback)        → 0.6
    Layer 6: Assume NSE                            → 0.4
    """

    def resolve(
        self, raw: str
    ) -> Tuple[Optional[str], float]:
        """
        Returns (resolved_symbol, confidence_score)
        confidence: 0.0 - 1.0
        """
        if not raw or not raw.strip():
            return None, 0.0

        cleaned = raw.strip().upper()

        # Layer 1: Already has exchange suffix
        if cleaned.endswith(".NS") or cleaned.endswith(".BO"):
            self._save_alias(raw, cleaned, 1.0, "exact")
            return cleaned, 1.0

        # Layer 1b: Known US stock
        if cleaned in US_STOCKS:
            self._save_alias(raw, cleaned, 1.0, "exact")
            return cleaned, 1.0

        # Layer 2: DB alias cache
        cached = self._lookup_alias(cleaned)
        if cached:
            return cached["resolved_symbol"], cached["confidence"]

        # Layer 3: Static map
        if cleaned in STATIC_MAP:
            resolved = STATIC_MAP[cleaned]
            self._save_alias(raw, resolved, 0.95, "static_map")
            return resolved, 0.95

        # Layer 4: Fuzzy match against static map keys
        resolved, score = self._fuzzy_match(cleaned)
        if resolved and score >= 0.80:
            confidence = 0.7 + (score - 0.80) * 1.5
            confidence = min(confidence, 0.90)
            self._save_alias(raw, resolved, confidence, "fuzzy")
            return resolved, round(confidence, 3)

        # Layer 5: yfinance search
        resolved = self._yfinance_search(cleaned)
        if resolved:
            self._save_alias(raw, resolved, 0.65, "yfinance")
            return resolved, 0.65

        # Layer 6: Assume NSE
        assumed = f"{cleaned}.NS"
        self._save_alias(raw, assumed, 0.40, "assumed_nse")
        logger.warning(
            f"Could not confidently resolve '{raw}' "
            f"→ assuming '{assumed}' (confidence: 0.40)"
        )
        return assumed, 0.40

    def _lookup_alias(self, raw: str) -> Optional[dict]:
        """Check DB for previously resolved alias."""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT resolved_symbol, confidence
                FROM symbol_aliases
                WHERE raw_input = ?
            """, (raw,)).fetchone()
            if row:
                # Increment use count
                conn.execute("""
                    UPDATE symbol_aliases
                    SET use_count = use_count + 1
                    WHERE raw_input = ?
                """, (raw,))
                conn.commit()
                return dict(row)
            return None
        finally:
            conn.close()

    def _save_alias(
        self, raw: str, resolved: str,
        confidence: float, source: str
    ):
        """Save resolved mapping to DB for future use."""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO symbol_aliases
                    (raw_input, resolved_symbol,
                     confidence, source)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(raw_input) DO UPDATE SET
                    resolved_symbol = excluded.resolved_symbol,
                    confidence = excluded.confidence,
                    use_count = use_count + 1
            """, (raw.upper(), resolved, confidence, source))
            conn.commit()
        except Exception as e:
            logger.debug(f"Alias save failed: {e}")
        finally:
            conn.close()

    def _fuzzy_match(
        self, raw: str
    ) -> Tuple[Optional[str], float]:
        """Fuzzy match raw symbol against known symbols."""
        try:
            from rapidfuzz import process, fuzz
            candidates = list(STATIC_MAP.keys())
            result = process.extractOne(
                raw,
                candidates,
                scorer=fuzz.WRatio,
                score_cutoff=75
            )
            if result:
                match_key, score, _ = result
                return STATIC_MAP[match_key], score / 100
        except ImportError:
            logger.debug("rapidfuzz not installed, skipping fuzzy match")
        return None, 0.0

    def _yfinance_search(
        self, query: str
    ) -> Optional[str]:
        """Use yfinance to search for symbol."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{query}.NS")
            info = ticker.fast_info
            if hasattr(info, "last_price") and info.last_price:
                return f"{query}.NS"
            # Try US
            ticker = yf.Ticker(query)
            info = ticker.fast_info
            if hasattr(info, "last_price") and info.last_price:
                return query
        except Exception:
            pass
        return None


# Singleton instance
resolver = SmartSymbolResolver()


def resolve_symbol(raw: str) -> Tuple[Optional[str], float]:
    """Convenience function."""
    return resolver.resolve(raw)


def detect_exchange(symbol: str) -> str:
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith(".BO"):
        return "BSE"
    if symbol in US_STOCKS or "." not in symbol:
        return "US"
    return "NSE"


def detect_currency(symbol: str) -> str:
    return "USD" if detect_exchange(symbol) == "US" else "INR"