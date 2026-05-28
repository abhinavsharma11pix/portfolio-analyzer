"""
Free fundamental data using yfinance .info
Covers: PE, PB, EPS, revenue, margins, analyst ratings, dividend yield.
All cached aggressively — fundamentals change slowly.
"""
import logging
import yfinance as yf
from typing import Dict, Optional
from app.cache import store as cache

logger = logging.getLogger(__name__)

FUNDAMENTAL_TTL = 86400  # 24 hours — fundamentals rarely change intraday


def _safe(val, default=None):
    if val is None or val != val:
        return default
    try:
        return round(float(val), 4) if isinstance(val, (int, float)) else val
    except Exception:
        return default


def fetch_fundamentals(symbol: str) -> Dict:
    """
    Fetch full fundamental data for a single symbol.
    Uses yfinance .info — covers NSE, BSE and US stocks.
    """
    key    = f"fund:{symbol}"
    cached = cache.get(key, FUNDAMENTAL_TTL, disk=True)
    if cached:
        return cached

    try:
        info = yf.Ticker(symbol).info
        if not info or len(info) < 5:
            return _empty(symbol)

        result = {
            "symbol":             symbol,
            "name":               info.get("longName") or info.get("shortName", symbol),
            "sector":             info.get("sector", "Unknown"),
            "industry":           info.get("industry", "Unknown"),
            "country":            info.get("country", "Unknown"),
            "exchange":           info.get("exchange", ""),
            "currency":           info.get("currency", "INR"),
            "market_cap":         _safe(info.get("marketCap")),
            "market_cap_cr":      _safe_cr(info.get("marketCap"), info.get("currency","INR")),
            "enterprise_value":   _safe(info.get("enterpriseValue")),
            # Valuation
            "pe_ratio":           _safe(info.get("trailingPE")),
            "forward_pe":         _safe(info.get("forwardPE")),
            "pb_ratio":           _safe(info.get("priceToBook")),
            "ps_ratio":           _safe(info.get("priceToSalesTrailing12Months")),
            "peg_ratio":          _safe(info.get("pegRatio")),
            "ev_ebitda":          _safe(info.get("enterpriseToEbitda")),
            "ev_revenue":         _safe(info.get("enterpriseToRevenue")),
            # Earnings
            "eps_ttm":            _safe(info.get("trailingEps")),
            "eps_forward":        _safe(info.get("forwardEps")),
            "eps_growth_qoq":     _safe(info.get("earningsQuarterlyGrowth")),
            "revenue_growth":     _safe(info.get("revenueGrowth")),
            "earnings_growth":    _safe(info.get("earningsGrowth")),
            # Revenue
            "revenue_ttm":        _safe(info.get("totalRevenue")),
            "gross_margin":       _safe(info.get("grossMargins")),
            "operating_margin":   _safe(info.get("operatingMargins")),
            "profit_margin":      _safe(info.get("profitMargins")),
            "ebitda":             _safe(info.get("ebitda")),
            # Balance sheet
            "total_cash":         _safe(info.get("totalCash")),
            "total_debt":         _safe(info.get("totalDebt")),
            "debt_to_equity":     _safe(info.get("debtToEquity")),
            "current_ratio":      _safe(info.get("currentRatio")),
            "book_value":         _safe(info.get("bookValue")),
            "return_on_equity":   _safe(info.get("returnOnEquity")),
            "return_on_assets":   _safe(info.get("returnOnAssets")),
            # Dividends
            "dividend_yield":     _safe(info.get("dividendYield")),
            "dividend_rate":      _safe(info.get("dividendRate")),
            "payout_ratio":       _safe(info.get("payoutRatio")),
            "ex_dividend_date":   info.get("exDividendDate"),
            # Analyst ratings
            "analyst_rating":     info.get("recommendationKey", "").upper(),
            "analyst_mean_score": _safe(info.get("recommendationMean")),
            "target_price":       _safe(info.get("targetMeanPrice")),
            "target_high":        _safe(info.get("targetHighPrice")),
            "target_low":         _safe(info.get("targetLowPrice")),
            "num_analysts":       _safe(info.get("numberOfAnalystOpinions")),
            # Price stats
            "52w_high":           _safe(info.get("fiftyTwoWeekHigh")),
            "52w_low":            _safe(info.get("fiftyTwoWeekLow")),
            "52w_change":         _safe(info.get("52WeekChange")),
            "50d_avg":            _safe(info.get("fiftyDayAverage")),
            "200d_avg":           _safe(info.get("twoHundredDayAverage")),
            "avg_volume":         _safe(info.get("averageVolume")),
            "float_shares":       _safe(info.get("floatShares")),
            # Scores computed below
            "valuation_score":    None,
            "quality_score":      None,
            "growth_score":       None,
            "fundamental_grade":  None,
            "fundamental_summary": None,
        }

        # Compute scores
        result.update(_compute_scores(result))
        cache.set(key, result, FUNDAMENTAL_TTL, disk=True)
        return result

    except Exception as e:
        logger.warning(f"Fundamentals fetch failed for {symbol}: {e}")
        return _empty(symbol)


def fetch_fundamentals_batch(symbols: list) -> Dict[str, Dict]:
    """Fetch fundamentals for multiple symbols."""
    results = {}
    for sym in symbols:
        results[sym] = fetch_fundamentals(sym)
    return results


def _safe_cr(val, currency: str) -> Optional[float]:
    """Convert market cap to Crores for INR, Billions for USD."""
    if val is None:
        return None
    try:
        v = float(val)
        if currency in ("INR", "Rs"):
            return round(v / 1e7, 2)   # Crores
        return round(v / 1e9, 2)       # Billions
    except Exception:
        return None


def _compute_scores(d: Dict) -> Dict:
    """
    Compute fundamental scores (0–100) based on available metrics.
    Designed to work even with partial data.
    """
    # ── Valuation score (lower PE/PB = better value) ───────
    val_pts = 0
    val_cnt = 0
    pe = d.get("pe_ratio")
    if pe and pe > 0:
        if pe < 15:   val_pts += 30
        elif pe < 25: val_pts += 20
        elif pe < 40: val_pts += 10
        val_cnt += 1

    pb = d.get("pb_ratio")
    if pb and pb > 0:
        if pb < 2:   val_pts += 25
        elif pb < 4: val_pts += 15
        elif pb < 8: val_pts += 5
        val_cnt += 1

    peg = d.get("peg_ratio")
    if peg and 0 < peg < 10:
        if peg < 1:   val_pts += 25
        elif peg < 2: val_pts += 15
        elif peg < 3: val_pts += 5
        val_cnt += 1

    valuation_score = round(val_pts / max(val_cnt, 1)) if val_cnt else None

    # ── Quality score (margins, ROE, debt) ────────────────
    qual_pts = 0
    qual_cnt = 0

    roe = d.get("return_on_equity")
    if roe:
        if roe > 0.20:   qual_pts += 30
        elif roe > 0.12: qual_pts += 20
        elif roe > 0.05: qual_pts += 10
        qual_cnt += 1

    pm = d.get("profit_margin")
    if pm:
        if pm > 0.20:   qual_pts += 25
        elif pm > 0.10: qual_pts += 15
        elif pm > 0.03: qual_pts += 5
        qual_cnt += 1

    de = d.get("debt_to_equity")
    if de is not None:
        if de < 0.3:   qual_pts += 25
        elif de < 0.7: qual_pts += 15
        elif de < 1.5: qual_pts += 5
        qual_cnt += 1

    cr = d.get("current_ratio")
    if cr:
        if cr > 2:   qual_pts += 20
        elif cr > 1: qual_pts += 10
        qual_cnt += 1

    quality_score = round(qual_pts / max(qual_cnt, 1)) if qual_cnt else None

    # ── Growth score ──────────────────────────────────────
    grow_pts = 0
    grow_cnt = 0

    rg = d.get("revenue_growth")
    if rg is not None:
        if rg > 0.25:   grow_pts += 35
        elif rg > 0.10: grow_pts += 20
        elif rg > 0:    grow_pts += 10
        grow_cnt += 1

    eg = d.get("earnings_growth")
    if eg is not None:
        if eg > 0.25:   grow_pts += 35
        elif eg > 0.10: grow_pts += 20
        elif eg > 0:    grow_pts += 10
        grow_cnt += 1

    eps_g = d.get("eps_growth_qoq")
    if eps_g is not None:
        if eps_g > 0.15:  grow_pts += 30
        elif eps_g > 0.0: grow_pts += 15
        grow_cnt += 1

    growth_score = round(grow_pts / max(grow_cnt, 1)) if grow_cnt else None

    # ── Composite fundamental grade ───────────────────────
    available = [s for s in [valuation_score, quality_score, growth_score] if s is not None]
    composite = round(sum(available) / len(available)) if available else None

    grade = None
    if composite is not None:
        if composite >= 75: grade = "A"
        elif composite >= 60: grade = "B"
        elif composite >= 45: grade = "C"
        elif composite >= 30: grade = "D"
        else: grade = "F"

    summary = _build_summary(d, valuation_score, quality_score, growth_score, grade)

    return {
        "valuation_score":     valuation_score,
        "quality_score":       quality_score,
        "growth_score":        growth_score,
        "composite_fundamental": composite,
        "fundamental_grade":   grade,
        "fundamental_summary": summary,
    }


def _build_summary(d: Dict, v, q, g, grade) -> str:
    parts = []
    pe    = d.get("pe_ratio")
    roe   = d.get("return_on_equity")
    pm    = d.get("profit_margin")
    rg    = d.get("revenue_growth")
    dy    = d.get("dividend_yield")
    tp    = d.get("target_price")
    ar    = d.get("analyst_rating", "")

    if pe:
        parts.append(f"P/E {pe:.1f}")
    if roe:
        parts.append(f"ROE {roe*100:.1f}%")
    if pm:
        parts.append(f"Margin {pm*100:.1f}%")
    if rg:
        parts.append(f"Revenue growth {rg*100:+.1f}%")
    if dy and dy > 0:
        parts.append(f"Dividend yield {dy*100:.2f}%")
    if tp:
        parts.append(f"Analyst target ₹{tp:.0f}")
    if ar:
        parts.append(f"Analysts: {ar}")

    return " · ".join(parts) if parts else "Limited fundamental data available"


def _empty(symbol: str) -> Dict:
    return {
        "symbol": symbol, "name": symbol, "sector": "Unknown",
        "pe_ratio": None, "pb_ratio": None, "eps_ttm": None,
        "revenue_growth": None, "earnings_growth": None,
        "profit_margin": None, "return_on_equity": None,
        "debt_to_equity": None, "dividend_yield": None,
        "analyst_rating": None, "target_price": None,
        "52w_high": None, "52w_low": None,
        "valuation_score": None, "quality_score": None,
        "growth_score": None, "fundamental_grade": None,
        "fundamental_summary": "No fundamental data available",
        "composite_fundamental": None,
    }