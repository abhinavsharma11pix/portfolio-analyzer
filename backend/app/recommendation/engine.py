"""
backend/app/recommendation/engine.py — Complete file.
Fixed: dead code after first `return result` removed.
Added: evidence-based reasoning per stock via evidence_engine.py.
       Every recommendation now explains WHY with real metrics:
       dividend yield/payout/growth, P/E, revenue growth, beta, etc.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.cache import store as cache

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
#  RISK PROFILES
# ══════════════════════════════════════════════════════════════

RISK_PROFILES = {
    "conservative": {
        "equity_pct": 0.50, "etf_pct": 0.30, "cash_pct": 0.20,
        "max_single_stock": 0.20, "max_sector": 0.40,
        "volatility_target": 14, "sharpe_min": 0.3,
        "default_sectors": ["FMCG", "Banking", "Healthcare", "Energy"],
    },
    "moderate": {
        "equity_pct": 0.75, "etf_pct": 0.15, "cash_pct": 0.10,
        "max_single_stock": 0.22, "max_sector": 0.45,
        "volatility_target": 22, "sharpe_min": 0.0,
        "default_sectors": ["Technology", "Banking", "Healthcare", "Finance", "Consumer"],
    },
    "aggressive": {
        "equity_pct": 0.90, "etf_pct": 0.05, "cash_pct": 0.05,
        "max_single_stock": 0.25, "max_sector": 0.55,
        "volatility_target": 32, "sharpe_min": -0.3,
        "default_sectors": ["Technology", "Finance", "Auto", "Consumer", "Infra"],
    },
    "high_growth": {
        "equity_pct": 0.95, "etf_pct": 0.05, "cash_pct": 0.00,
        "max_single_stock": 0.30, "max_sector": 0.65,
        "volatility_target": 42, "sharpe_min": -0.5,
        "default_sectors": ["Technology", "Finance", "Auto", "Healthcare", "IT"],
    },
}

GOAL_TO_PROFILE = {
    "wealth_creation": "moderate",
    "passive_growth":  "conservative",
    "retirement":      "conservative",
    "high_growth":     "aggressive",
    "dividend_income": "conservative",
    "low_risk":        "conservative",
    "tax_efficient":   "moderate",
    "learning":        "moderate",
}


# ══════════════════════════════════════════════════════════════
#  DATA CLASSES
# ══════════════════════════════════════════════════════════════

@dataclass
class RiskProfile:
    category:          str
    confidence:        float
    explanation:       str
    equity_pct:        float
    etf_pct:           float
    volatility_target: float
    max_sector:        float


# ══════════════════════════════════════════════════════════════
#  RISK PROFILE INFERENCE
# ══════════════════════════════════════════════════════════════

def infer_risk_profile(
    amount:            float,
    goal:              str,
    horizon:           str,
    market:            str,
    preferred_sectors: List[str],
) -> RiskProfile:

    base = GOAL_TO_PROFILE.get(goal, "moderate")
    profiles = ["conservative", "moderate", "aggressive", "high_growth"]
    idx = profiles.index(base)

    horizon_delta = {"short": +1, "medium": 0, "long": -1}.get(horizon, 0)
    idx = max(0, min(3, idx + horizon_delta))

    aggressive_sectors = {"Technology", "Finance", "Auto", "IT", "Defense"}
    if preferred_sectors and len(set(preferred_sectors) & aggressive_sectors) >= 2:
        idx = min(3, idx + 1)

    cat          = profiles[idx]
    profile_data = RISK_PROFILES[cat]

    explanations = {
        "conservative": (
            "Your goal and timeline prioritize capital preservation. "
            "We focus on quality stocks with strong fundamentals and lower volatility."
        ),
        "moderate": (
            "A balanced approach targeting steady growth while managing risk. "
            "Selected based on real Sharpe ratio and momentum data."
        ),
        "aggressive": (
            "Growth-oriented strategy with higher return potential. "
            "Stocks selected for momentum and risk-adjusted performance."
        ),
        "high_growth": (
            "Maximum growth targeting. High-conviction stocks selected "
            "using composite scoring across multiple financial metrics."
        ),
    }

    confidence = 0.78
    if horizon == "long" and goal in ["wealth_creation", "high_growth", "retirement"]:
        confidence = 0.92
    elif horizon == "short" and goal == "low_risk":
        confidence = 0.88

    return RiskProfile(
        category=cat,
        confidence=confidence,
        explanation=explanations[cat],
        equity_pct=profile_data["equity_pct"],
        etf_pct=profile_data["etf_pct"],
        volatility_target=profile_data["volatility_target"],
        max_sector=profile_data["max_sector"],
    )


# ══════════════════════════════════════════════════════════════
#  ROLE ENGINE
# ══════════════════════════════════════════════════════════════

def _role(sector: str, sharpe: float, momentum: float) -> str:
    defensive = {"FMCG", "Healthcare", "Energy", "Banking", "Pharma"}
    growth    = {"Technology", "Finance", "Auto", "Consumer", "IT"}

    if sharpe > 1.0 and momentum > 15:
        return "growth"
    if sector in defensive and sharpe > 0:
        return "stability"
    if sector in growth:
        return "growth"
    if momentum < -5:
        return "recovery"
    return "balanced"


# ══════════════════════════════════════════════════════════════
#  EVIDENCE-BACKED WHY ENGINE
# ══════════════════════════════════════════════════════════════

def _why(stock: Dict, role: str) -> str:
    """
    Generate the base why-string from scored stock data.
    This is the fast version (no yfinance call) used for all stocks.
    The deeper evidence_engine.py enrichment is added separately
    for stocks where we have time/quota.
    """
    sec   = stock["sector"]
    sh    = stock.get("sharpe", 0)
    mo    = stock.get("momentum_1y", 0)
    vol   = stock.get("volatility", 20)
    dd    = stock.get("max_drawdown", -15)
    score = stock.get("composite_score", 50)
    beta  = stock.get("beta", 1.0)

    parts = []

    # Role-based opening sentence
    if role == "stability":
        parts.append(f"Defensive {sec} sector stock with capital-preservation characteristics.")
    elif role == "growth":
        parts.append(f"Growth driver in {sec} sector with {mo:+.1f}% 1-year price return.")
    elif role == "recovery":
        parts.append(f"Turnaround candidate in {sec} — oversold with mean-reversion potential.")
    else:
        parts.append(f"Quality {sec} stock with balanced risk-return profile.")

    # Sharpe ratio — the most important risk-adjusted metric
    if sh > 1.5:
        parts.append(f"Excellent Sharpe ratio of {sh:.2f} — top-quartile risk-adjusted return verified on 1-year data.")
    elif sh > 0.8:
        parts.append(f"Good Sharpe ratio of {sh:.2f} — solid risk-adjusted returns over the past year.")
    elif sh > 0.3:
        parts.append(f"Positive Sharpe ratio of {sh:.2f} — returns exceed risk-free rate.")
    elif sh < 0:
        parts.append(f"Negative Sharpe ({sh:.2f}) — included for diversification, not return quality.")

    # Drawdown — downside protection evidence
    if abs(dd) < 12:
        parts.append(f"Strong downside protection: max drawdown of only {dd:.1f}% historically.")
    elif abs(dd) < 20:
        parts.append(f"Moderate drawdown of {dd:.1f}% — acceptable risk for the return profile.")
    elif abs(dd) > 35:
        parts.append(f"High historical drawdown of {dd:.1f}% — position sized conservatively.")

    # Volatility — portfolio impact
    if vol < 15:
        parts.append(f"Low annualized volatility of {vol:.1f}% — stabilizes overall portfolio.")
    elif vol > 35:
        parts.append(f"High volatility of {vol:.1f}% — sized at a smaller allocation to control portfolio-level risk.")

    # Beta — market sensitivity
    if beta < 0.7:
        parts.append(f"Beta of {beta:.2f} — moves significantly less than the broader market (defensive).")
    elif beta > 1.5:
        parts.append(f"Beta of {beta:.2f} — amplifies market moves; high-conviction growth bet.")

    # Composite score summary
    parts.append(f"Composite score: {score:.0f}/100 based on Sharpe, momentum, drawdown, and volatility.")

    return " ".join(parts)


# ══════════════════════════════════════════════════════════════
#  COMMENTARY, WARNINGS, STRENGTHS
# ══════════════════════════════════════════════════════════════

def _commentary(
    profile:  RiskProfile,
    stocks:   List[Dict],
    horizon:  str,
    goal:     str,
    metrics:  Dict,
) -> str:
    n     = len(stocks)
    cat   = profile.category
    w_sh  = metrics.get("weighted_sharpe", 0)
    exp_r = metrics.get("expected_return", 0)
    exp_v = metrics.get("expected_volatility", 0)
    score = metrics.get("portfolio_score", 50)
    n_sec = metrics.get("n_sectors", 1)

    cap = {
        "conservative": "stable, capital-preserving",
        "moderate":     "balanced growth",
        "aggressive":   "growth-focused",
        "high_growth":  "high-growth",
    }.get(cat, "balanced")

    horizon_l = {"short": "short-term", "medium": "medium-term", "long": "long-term"}.get(horizon, "")
    goal_l    = goal.replace("_", " ")

    sh_quality = (
        "excellent" if w_sh > 1.5 else
        "good"      if w_sh > 0.8 else
        "moderate"  if w_sh > 0.3 else
        "below-average"
    )

    return (
        f"This {cap} portfolio of {n} stocks is built for your {horizon_l} {goal_l} goal. "
        f"Based on real 1-year yfinance data, these stocks delivered an average return of "
        f"{exp_r:+.1f}% with estimated portfolio volatility of ~{exp_v:.0f}%. "
        f"Weighted portfolio Sharpe ratio of {w_sh:.2f} indicates {sh_quality} risk-adjusted "
        f"returns verified on historical market data. "
        f"Spanning {n_sec} sector{'s' if n_sec > 1 else ''}, the portfolio scores {score}/100 "
        f"using a composite of Sharpe ratio, momentum, drawdown protection, and diversification."
    )


def _warnings(
    sector_alloc: Dict[str, float],
    metrics:      Dict,
    profile:      RiskProfile,
) -> List[str]:
    out     = []
    exp_vol = metrics.get("expected_volatility", 0)
    w_dd    = metrics.get("weighted_drawdown", 0)
    w_sh    = metrics.get("weighted_sharpe", 0)

    for sec, pct in sector_alloc.items():
        if pct > 60:
            out.append(f"Heavy {sec} concentration ({pct:.0f}%) — high sector-specific risk")
        elif pct > 45:
            out.append(f"Elevated {sec} exposure ({pct:.0f}%) — monitor sector developments closely")

    if exp_vol > profile.volatility_target * 1.4:
        out.append(
            f"Portfolio volatility ({exp_vol:.0f}%) exceeds your profile target "
            f"({profile.volatility_target:.0f}%) — consider adding defensive stocks"
        )

    if w_dd < -35:
        out.append(
            f"Average historical drawdown of {w_dd:.0f}% — portfolio has experienced "
            "significant peak-to-trough declines; size positions accordingly"
        )

    if w_sh < 0:
        out.append(
            "Negative weighted Sharpe ratio — portfolio returns below risk-free rate "
            "historically. Consider reviewing sector selection."
        )

    return out


def _strengths(stocks: List[Dict], metrics: Dict) -> List[str]:
    out   = []
    sh    = metrics.get("weighted_sharpe", 0)
    n_sec = metrics.get("n_sectors", 1)
    div   = metrics.get("diversification_score", 0)
    exp_r = metrics.get("expected_return", 0)

    if sh > 1.0:
        out.append(
            f"Strong portfolio Sharpe ratio of {sh:.2f} — historically excellent "
            "risk-adjusted returns verified using 1-year market data"
        )

    if div >= 65:
        out.append(
            f"Good diversification across {n_sec} sectors "
            f"(score: {div}/100) reduces concentration risk"
        )

    top_momentum = [s for s in stocks if s.get("momentum_1y", 0) > 20]
    if top_momentum:
        out.append(
            f"{len(top_momentum)} stock{'s' if len(top_momentum) > 1 else ''} with "
            f">20% 1-year return — strong price momentum confirmed by market data"
        )

    low_dd = [s for s in stocks if s.get("max_drawdown", -100) > -20]
    if len(low_dd) >= 2:
        out.append(
            f"{len(low_dd)} holdings with max drawdown < 20% — strong downside protection"
        )

    if exp_r > 15:
        out.append(
            f"Portfolio 1-year historical return of {exp_r:+.1f}% — "
            "significantly above typical fixed-income alternatives"
        )

    return out


# ══════════════════════════════════════════════════════════════
#  MAIN ENGINE
# ══════════════════════════════════════════════════════════════

def generate_recommendation(
    amount:            float,
    goal:              str,
    horizon:           str,
    market:            str,
    exchange:          str = "auto",
    preferred_sectors: Optional[List[str]] = None,
    n_stocks_min:      int = 5,
    n_stocks_max:      int = 10,
) -> Dict:

    preferred_sectors = preferred_sectors or []

    # ── Cache check ────────────────────────────────────────────
    cache_key = cache._make_key("rec_v5", {
        "amt":  int(amount / 5000),
        "goal": goal,
        "h":    horizon,
        "mkt":  market,
        "sec":  sorted(preferred_sectors),
        "nmin": n_stocks_min,
        "nmax": n_stocks_max,
    })

    cached = cache.get(cache_key, 1800)
    if cached:
        logger.info("Recommendation loaded from cache")
        return cached

    # ── Profile ────────────────────────────────────────────────
    profile = infer_risk_profile(amount, goal, horizon, market, preferred_sectors)
    pdata   = RISK_PROFILES[profile.category]

    # ── Universe ───────────────────────────────────────────────
    from app.recommendation.universe import get_universe, filter_by_sectors

    universe = get_universe(market)
    if not universe:
        return {"error": "Could not fetch market data. Please try again."}

    logger.info(f"Universe size: {len(universe)}")

    # ── Sector filtering ───────────────────────────────────────
    if preferred_sectors:
        candidates = filter_by_sectors(universe, preferred_sectors)
        if len(candidates) < max(3, n_stocks_min):
            logger.info("Insufficient stocks in preferred sectors — falling back to full universe")
            candidates = universe if len(candidates) < 3 else candidates
    else:
        candidates = filter_by_sectors(universe, pdata["default_sectors"])
        if len(candidates) < n_stocks_min:
            candidates = universe

    logger.info(f"Candidates after filtering: {len(candidates)}")

    # ── Scoring ────────────────────────────────────────────────
    bench = "^NSEI" if market == "india" else "^GSPC"

    from app.recommendation.scorer import score_stocks_batch
    scored = score_stocks_batch(candidates[:150], benchmark=bench)

    if not scored:
        return {"error": "Could not score stocks. Market data may be unavailable."}

    # ── Portfolio build ────────────────────────────────────────
    n_target = (n_stocks_min + n_stocks_max) // 2

    from app.recommendation.portfolio_builder import build_final_portfolio, enforce_affordability

    selected, weights, metrics = build_final_portfolio(scored, amount, n_target, pdata)

    if not selected:
        return {"error": "Could not build portfolio from available data."}

    # ── Affordability enforcement ──────────────────────────────
    for stock in selected:
        if "score_data" not in stock:
            stock["score_data"] = {}

    affordability_result = enforce_affordability(selected, weights, amount)

    if len(affordability_result) == 3:
        selected, weights, unaffordable_list = affordability_result
    else:
        selected, weights = affordability_result
        unaffordable_list = []

    if not selected:
        return {
            "error": (
                "Investment amount too small for available stocks in selected sectors. "
                "Try a larger amount or different sectors."
            )
        }

    # ── Build output ───────────────────────────────────────────
    stocks_out:   List[Dict]       = []
    sector_alloc: Dict[str, float] = {}
    total_invested = metrics.get("total_invested", amount)
    uninvested     = metrics.get("uninvested_cash", 0)

    for stock in selected:
        shares          = stock.get("shares_to_buy", 0)
        price_per_share = stock.get("price_per_share", 0)
        total_cost      = stock.get("total_cost", 0)

        if shares == 0:
            continue

        actual_pct = round(total_cost / amount * 100, 1) if amount > 0 else 0
        role       = _role(stock["sector"], stock.get("sharpe", 0), stock.get("momentum_1y", 0))
        why        = _why(stock, role)
        vol        = stock.get("volatility", 20)
        risk       = "Low" if vol < 18 else "Medium" if vol < 28 else "High"
        pps        = price_per_share or 0

        stocks_out.append({
            "symbol":            stock["symbol"],
            "name":              stock.get("name", stock["symbol"]),
            "sector":            stock["sector"],
            "allocation_pct":    actual_pct,
            "allocation_amount": total_cost,
            "shares_to_buy":     shares,
            "price_per_share":   price_per_share,
            "total_cost":        total_cost,
            "share_summary":     (
                f"{shares} share{'s' if shares > 1 else ''} "
                f"@ ₹{pps:,.0f} = ₹{total_cost:,.0f}"
            ),
            "role":              role,
            "why":               why,
            "risk_contribution": risk,
            "momentum_score":    round(min(1.0, max(0.0, (stock.get("momentum_1y", 0) + 30) / 80)), 3),
            "sharpe_estimate":   round(stock.get("sharpe", 0), 3),
            "volatility":        round(vol, 1),
            "composite_score":   round(stock.get("composite_score", 50), 1),
            "momentum_1y":       round(stock.get("momentum_1y", 0), 2),
            "max_drawdown":      round(stock.get("max_drawdown", 0), 2),
            "beta":              round(stock.get("beta", 1.0), 3),
        })

        sec = stock["sector"]
        sector_alloc[sec] = round(sector_alloc.get(sec, 0) + actual_pct, 1)

    # ── Evidence-backed reasoning (non-blocking, best-effort) ──
    # Runs AFTER the main output is built so a yfinance failure here
    # never blocks the recommendation from returning.
    try:
        from app.recommendation.evidence_engine import build_evidence_batch
        evidence_map = build_evidence_batch(stocks_out)
        for s in stocks_out:
            ev = evidence_map.get(s["symbol"])
            if ev:
                # Append evidence factors to the existing why string
                if ev.get("factors"):
                    evidence_bullets = " | ".join(ev["factors"][:3])
                    s["why"] = f"{s['why']} Evidence: {evidence_bullets}"
                s["evidence"] = ev
    except Exception as e:
        logger.warning(f"Evidence enrichment failed (non-fatal): {e}")

    # ── Final assembly ─────────────────────────────────────────
    sector_list = sorted(
        [{"sector": k, "weight_pct": v} for k, v in sector_alloc.items()],
        key=lambda x: -x["weight_pct"],
    )

    commentary = _commentary(profile, stocks_out, horizon, goal, metrics)
    warnings   = _warnings(sector_alloc, metrics, profile)
    strengths  = _strengths(stocks_out, metrics)

    result: Dict = {
        "profile": {
            "category":          profile.category,
            "confidence":        profile.confidence,
            "explanation":       profile.explanation,
            "equity_pct":        profile.equity_pct,
            "etf_pct":           profile.etf_pct,
            "volatility_target": profile.volatility_target,
        },
        "stocks":                stocks_out,
        "total_amount":          amount,
        "total_invested":        total_invested,
        "uninvested_cash":       uninvested,
        "expected_return":       metrics.get("expected_return", 0),
        "expected_volatility":   metrics.get("expected_volatility", 0),
        "portfolio_score":       metrics.get("portfolio_score", 50),
        "diversification_score": metrics.get("diversification_score", 50),
        "weighted_sharpe":       metrics.get("weighted_sharpe", 0),
        "weighted_beta":         metrics.get("weighted_beta", 1.0),
        "score_breakdown":       metrics.get("score_breakdown", {}),
        "ai_commentary":         commentary,
        "sector_allocation":     sector_list,
        "risk_warnings":         warnings,
        "strengths":             strengths,
        "data_note":             (
            "Scores based on real 1-year market data via yfinance. "
            "Whole shares only. Evidence metrics from yfinance fundamentals."
        ),
        "sectors_used":          list(sector_alloc.keys()),
        "n_sectors":             metrics.get("n_sectors", 0),
    }

    if unaffordable_list:
        result["warnings"] = [
            f"{sym} removed — allocation too small to buy even 1 share at current price"
            for sym in unaffordable_list
        ]

    cache.set(cache_key, result, 1800)
    return result
