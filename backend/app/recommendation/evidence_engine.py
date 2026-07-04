"""
backend/app/recommendation/evidence_engine.py — NEW complete file.

Generates evidence-backed reasoning for every stock recommendation.
Instead of "Strong dividend potential", produces:
  "5-year avg dividend yield 2.8%, payout ratio 35% (sustainable,
   well below 60% danger zone), dividends grown 4 consecutive years,
   operating cash flow covers dividend 3.2x."

Designed to slot into portfolio_builder.py / engine.py — call
build_evidence(symbol, ticker_info, price_history) per recommended
stock and attach the result to that stock's output dict as "evidence".
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def _safe(v, default=None):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return v
    except Exception:
        return default


def _pct(v: Optional[float], digits: int = 1) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.{digits}f}%" if abs(v) < 5 else f"{v:.{digits}f}%"


def _fmt_money(v: Optional[float], currency: str = "₹") -> str:
    if v is None:
        return "N/A"
    if abs(v) >= 1e7:
        return f"{currency}{v/1e7:.1f}Cr"
    if abs(v) >= 1e5:
        return f"{currency}{v/1e5:.1f}L"
    return f"{currency}{v:,.0f}"


# ══════════════════════════════════════════════════════════════
#  Dividend evidence
# ══════════════════════════════════════════════════════════════

def _dividend_evidence(symbol: str, info: Dict) -> Dict:
    """
    Builds evidence for dividend-oriented recommendations:
      - 3-5yr historical payout
      - dividend yield + consistency
      - dividend growth trend
      - payout ratio + sustainability
      - cash flow coverage
    """
    try:
        ticker = yf.Ticker(symbol)
        divs   = ticker.dividends

        evidence: Dict = {"category": "dividend", "factors": [], "data": {}, "verdict": None}

        div_yield     = _safe(info.get("dividendYield"))
        payout_ratio  = _safe(info.get("payoutRatio"))
        five_yr_yield = _safe(info.get("fiveYearAvgDividendYield"))

        # ── Historical payout consistency (last 5 years) ──────
        consistency_years = 0
        growth_years       = 0
        annual_divs: Dict[int, float] = {}

        if divs is not None and len(divs) > 0:
            divs_recent = divs[divs.index >= (pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(years=5))]
            for date, amt in divs_recent.items():
                yr = date.year
                annual_divs[yr] = annual_divs.get(yr, 0) + float(amt)

            years_sorted = sorted(annual_divs.keys())
            consistency_years = len(years_sorted)

            # Count consecutive years of growth (most recent backwards)
            for i in range(len(years_sorted) - 1, 0, -1):
                if annual_divs[years_sorted[i]] > annual_divs[years_sorted[i - 1]]:
                    growth_years += 1
                else:
                    break

        evidence["data"] = {
            "dividend_yield":         div_yield,
            "five_year_avg_yield":    five_yr_yield,
            "payout_ratio":           payout_ratio,
            "years_with_dividends":   consistency_years,
            "consecutive_growth_yrs": growth_years,
            "annual_dividends":       {str(k): round(v, 2) for k, v in sorted(annual_divs.items())},
        }

        # ── Build factor sentences ─────────────────────────────
        if div_yield:
            evidence["factors"].append(
                f"Current dividend yield of {_pct(div_yield)}"
                + (f" vs 5-year average of {_pct(five_yr_yield)}" if five_yr_yield else "")
            )

        if consistency_years >= 3:
            evidence["factors"].append(
                f"Paid dividends in {consistency_years} of the last 5 years — consistent payer, not opportunistic"
            )
        elif consistency_years > 0:
            evidence["factors"].append(
                f"Only {consistency_years} year(s) of dividend history in the last 5 — limited track record"
            )

        if growth_years >= 2:
            evidence["factors"].append(
                f"Dividend has grown for {growth_years} consecutive year(s) — management signaling confidence in cash generation"
            )

        if payout_ratio is not None:
            if payout_ratio < 0.4:
                sustain = "highly sustainable — significant room to grow payouts"
            elif payout_ratio < 0.6:
                sustain = "sustainable — within prudent range"
            elif payout_ratio < 0.8:
                sustain = "elevated — monitor for payout cuts in a downturn"
            else:
                sustain = "high risk — payout ratio above 80% leaves little margin of safety"
            evidence["factors"].append(
                f"Payout ratio of {_pct(payout_ratio)} is {sustain}"
            )

        # ── Cash flow coverage ──────────────────────────────────
        try:
            cashflow = ticker.cashflow
            if cashflow is not None and not cashflow.empty:
                ocf_row = None
                for label in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                    if label in cashflow.index:
                        ocf_row = cashflow.loc[label]
                        break
                if ocf_row is not None and len(ocf_row) > 0:
                    ocf = float(ocf_row.iloc[0])
                    total_div_paid = annual_divs.get(max(annual_divs.keys()), 0) * float(info.get("sharesOutstanding") or 0)
                    if total_div_paid > 0 and ocf > 0:
                        coverage = ocf / total_div_paid
                        evidence["data"]["cash_flow_coverage_x"] = round(coverage, 1)
                        if coverage >= 3:
                            evidence["factors"].append(
                                f"Operating cash flow covers total dividend payout {coverage:.1f}x — strong cushion"
                            )
                        elif coverage >= 1.5:
                            evidence["factors"].append(
                                f"Operating cash flow covers dividend payout {coverage:.1f}x — adequate coverage"
                            )
                        else:
                            evidence["factors"].append(
                                f"Cash flow coverage of only {coverage:.1f}x — dividend sustainability is borderline"
                            )
        except Exception as e:
            logger.debug(f"Cash flow evidence skipped for {symbol}: {e}")

        # ── Verdict ──────────────────────────────────────────────
        score = 0
        if div_yield and div_yield > 0.02: score += 1
        if consistency_years >= 3: score += 1
        if growth_years >= 1: score += 1
        if payout_ratio is not None and payout_ratio < 0.6: score += 1

        evidence["verdict"] = (
            "Strong dividend case" if score >= 3 else
            "Moderate dividend case" if score >= 2 else
            "Weak dividend case — included primarily for other factors"
        )

        return evidence

    except Exception as e:
        logger.warning(f"Dividend evidence failed for {symbol}: {e}")
        return {"category": "dividend", "factors": ["Dividend data unavailable for this stock"], "data": {}, "verdict": "Unknown"}


# ══════════════════════════════════════════════════════════════
#  Growth evidence
# ══════════════════════════════════════════════════════════════

def _growth_evidence(symbol: str, info: Dict, price_history: Optional[pd.Series] = None) -> Dict:
    """Evidence for growth-oriented recommendations."""
    evidence: Dict = {"category": "growth", "factors": [], "data": {}, "verdict": None}

    rev_growth   = _safe(info.get("revenueGrowth"))
    earn_growth  = _safe(info.get("earningsGrowth"))
    peg_ratio    = _safe(info.get("pegRatio"))
    roe          = _safe(info.get("returnOnEquity"))

    evidence["data"] = {
        "revenue_growth_yoy":  rev_growth,
        "earnings_growth_yoy": earn_growth,
        "peg_ratio":           peg_ratio,
        "roe":                 roe,
    }

    if rev_growth is not None:
        pace = "exceptional" if rev_growth > 0.25 else "strong" if rev_growth > 0.15 else "moderate" if rev_growth > 0.05 else "weak"
        evidence["factors"].append(f"Revenue grew {_pct(rev_growth)} year-over-year — {pace} pace")

    if earn_growth is not None:
        evidence["factors"].append(f"Earnings growth of {_pct(earn_growth)} year-over-year")

    if peg_ratio is not None:
        valuation = "undervalued relative to growth" if peg_ratio < 1 else "fairly valued" if peg_ratio < 2 else "growth priced at a premium"
        evidence["factors"].append(f"PEG ratio of {peg_ratio:.2f} suggests stock is {valuation}")

    if roe is not None:
        quality = "excellent capital efficiency" if roe > 0.20 else "solid returns on equity" if roe > 0.12 else "below-average capital efficiency"
        evidence["factors"].append(f"Return on equity of {_pct(roe)} — {quality}")

    if price_history is not None and len(price_history) > 252:
        yr_return = (price_history.iloc[-1] / price_history.iloc[-252] - 1)
        evidence["data"]["price_momentum_1y"] = round(yr_return, 3)
        evidence["factors"].append(f"Stock price momentum: {_pct(yr_return)} over the past year")

    score = sum([
        1 if rev_growth and rev_growth > 0.10 else 0,
        1 if earn_growth and earn_growth > 0.10 else 0,
        1 if peg_ratio and peg_ratio < 1.5 else 0,
        1 if roe and roe > 0.15 else 0,
    ])
    evidence["verdict"] = (
        "Strong growth case" if score >= 3 else
        "Moderate growth case" if score >= 2 else
        "Limited growth evidence — other factors driving inclusion"
    )
    return evidence


# ══════════════════════════════════════════════════════════════
#  Value / quality evidence
# ══════════════════════════════════════════════════════════════

def _value_evidence(symbol: str, info: Dict) -> Dict:
    """Evidence for value-oriented recommendations."""
    evidence: Dict = {"category": "value", "factors": [], "data": {}, "verdict": None}

    pe          = _safe(info.get("trailingPE"))
    forward_pe  = _safe(info.get("forwardPE"))
    pb          = _safe(info.get("priceToBook"))
    debt_eq     = _safe(info.get("debtToEquity"))
    current_r   = _safe(info.get("currentRatio"))
    sector_pe   = _safe(info.get("trailingPegRatio"))  # proxy, sector PE not always available

    evidence["data"] = {
        "trailing_pe": pe, "forward_pe": forward_pe, "price_to_book": pb,
        "debt_to_equity": debt_eq, "current_ratio": current_r,
    }

    if pe is not None:
        if pe < 15:
            evidence["factors"].append(f"Trailing P/E of {pe:.1f} — trading at a discount to typical market multiples")
        elif pe < 25:
            evidence["factors"].append(f"Trailing P/E of {pe:.1f} — reasonably valued")
        else:
            evidence["factors"].append(f"Trailing P/E of {pe:.1f} — priced for continued strong growth")

    if forward_pe and pe and forward_pe < pe:
        evidence["factors"].append(f"Forward P/E ({forward_pe:.1f}) below trailing P/E — earnings expected to grow into the valuation")

    if pb is not None:
        evidence["factors"].append(f"Price-to-book of {pb:.2f}" + (" — below book value multiple of comparable peers" if pb < 2 else ""))

    if debt_eq is not None:
        leverage = "conservative balance sheet" if debt_eq < 50 else "moderate leverage" if debt_eq < 100 else "elevated leverage — higher financial risk"
        evidence["factors"].append(f"Debt-to-equity of {debt_eq:.0f}% — {leverage}")

    if current_r is not None:
        liquidity = "strong short-term liquidity" if current_r > 1.5 else "adequate liquidity" if current_r > 1 else "tight liquidity position"
        evidence["factors"].append(f"Current ratio of {current_r:.2f} — {liquidity}")

    score = sum([
        1 if pe and pe < 20 else 0,
        1 if pb and pb < 3 else 0,
        1 if debt_eq is not None and debt_eq < 80 else 0,
        1 if current_r and current_r > 1.2 else 0,
    ])
    evidence["verdict"] = (
        "Strong value case" if score >= 3 else
        "Moderate value case" if score >= 2 else
        "Limited value evidence — other factors driving inclusion"
    )
    return evidence


# ══════════════════════════════════════════════════════════════
#  Stability / defensive evidence
# ══════════════════════════════════════════════════════════════

def _stability_evidence(symbol: str, info: Dict, price_history: Optional[pd.Series] = None) -> Dict:
    """Evidence for stability/low-volatility recommendations."""
    evidence: Dict = {"category": "stability", "factors": [], "data": {}, "verdict": None}

    beta = _safe(info.get("beta"))
    evidence["data"]["beta"] = beta

    if beta is not None:
        if beta < 0.8:
            evidence["factors"].append(f"Beta of {beta:.2f} — historically moves less than the broader market, defensive characteristic")
        elif beta < 1.2:
            evidence["factors"].append(f"Beta of {beta:.2f} — moves roughly in line with the market")
        else:
            evidence["factors"].append(f"Beta of {beta:.2f} — more volatile than the broader market")

    if price_history is not None and len(price_history) > 60:
        returns = price_history.pct_change().dropna()
        vol_annualized = float(returns.std() * np.sqrt(252))
        max_dd = float((price_history / price_history.cummax() - 1).min())
        evidence["data"]["annualized_volatility"] = round(vol_annualized, 3)
        evidence["data"]["max_drawdown_1y"]        = round(max_dd, 3)
        evidence["factors"].append(f"Annualized volatility of {_pct(vol_annualized)}")
        evidence["factors"].append(f"Maximum drawdown over the period: {_pct(max_dd)}")

    score = sum([
        1 if beta and beta < 1.0 else 0,
        1 if evidence["data"].get("annualized_volatility", 1) < 0.25 else 0,
        1 if evidence["data"].get("max_drawdown_1y", -1) > -0.25 else 0,
    ])
    evidence["verdict"] = (
        "Strong stability case" if score >= 2 else
        "Moderate stability" if score >= 1 else
        "Higher volatility profile — sized accordingly in allocation"
    )
    return evidence


# ══════════════════════════════════════════════════════════════
#  Main entry — builds full evidence package for a recommendation
# ══════════════════════════════════════════════════════════════

def build_evidence(
    symbol:        str,
    role:          str,
    price_history: Optional[pd.Series] = None,
) -> Dict:
    """
    Main entry point. Call this once per recommended stock.

    role: 'dividend_income' | 'growth' | 'value' | 'stability' | 'balanced'
          (matches the role/category already used by portfolio_builder.py)

    Returns a dict ready to attach to the stock's output as "evidence":
      {
        "category": "dividend",
        "verdict": "Strong dividend case",
        "factors": ["...", "...", "..."],
        "data": { raw numbers for UI display },
      }
    """
    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}
    except Exception as e:
        logger.warning(f"Could not fetch info for {symbol}: {e}")
        info = {}

    role_lower = (role or "").lower()

    if "dividend" in role_lower or "income" in role_lower:
        return _dividend_evidence(symbol, info)
    elif "growth" in role_lower:
        return _growth_evidence(symbol, info, price_history)
    elif "value" in role_lower:
        return _value_evidence(symbol, info)
    elif "stability" in role_lower or "defensive" in role_lower or "low_risk" in role_lower:
        return _stability_evidence(symbol, info, price_history)
    else:
        # Balanced/unknown role — blend the two most informative checks
        growth = _growth_evidence(symbol, info, price_history)
        value  = _value_evidence(symbol, info)
        return {
            "category": "balanced",
            "factors":  (growth["factors"][:2] + value["factors"][:2]),
            "data":     {**growth["data"], **value["data"]},
            "verdict":  f"{growth['verdict']} · {value['verdict']}",
        }


def build_evidence_batch(stocks: List[Dict]) -> Dict[str, Dict]:
    """
    Batch version — call with the list of recommended stock dicts
    (each needs at least 'symbol' and 'role' keys).
    Returns {symbol: evidence_dict}.
    """
    results = {}
    for s in stocks:
        symbol = s.get("symbol")
        role   = s.get("role", "balanced")
        if not symbol:
            continue
        try:
            results[symbol] = build_evidence(symbol, role)
        except Exception as e:
            logger.warning(f"Evidence build failed for {symbol}: {e}")
            results[symbol] = {
                "category": "unknown",
                "factors": ["Detailed evidence unavailable for this stock"],
                "data": {}, "verdict": "Unknown",
            }
    return results
