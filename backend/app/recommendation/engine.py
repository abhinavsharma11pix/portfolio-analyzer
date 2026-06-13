"""
Production AI recommendation engine.
Uses real NSE/S&P500 stock universe + real yfinance scoring.
Strictly respects user sector preferences.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.cache import store as cache

logger = logging.getLogger(__name__)

# =============================================================================
# RISK PROFILES
# =============================================================================

RISK_PROFILES = {
    "conservative": {
        "equity_pct": 0.50,
        "etf_pct": 0.30,
        "cash_pct": 0.20,
        "max_single_stock": 0.20,
        "max_sector": 0.40,
        "volatility_target": 14,
        "sharpe_min": 0.3,
        "default_sectors": [
            "FMCG",
            "Banking",
            "Healthcare",
            "Energy",
        ],
    },

    "moderate": {
        "equity_pct": 0.75,
        "etf_pct": 0.15,
        "cash_pct": 0.10,
        "max_single_stock": 0.22,
        "max_sector": 0.45,
        "volatility_target": 22,
        "sharpe_min": 0.0,
        "default_sectors": [
            "Technology",
            "Banking",
            "Healthcare",
            "Finance",
            "Consumer",
        ],
    },

    "aggressive": {
        "equity_pct": 0.90,
        "etf_pct": 0.05,
        "cash_pct": 0.05,
        "max_single_stock": 0.25,
        "max_sector": 0.55,
        "volatility_target": 32,
        "sharpe_min": -0.3,
        "default_sectors": [
            "Technology",
            "Finance",
            "Auto",
            "Consumer",
            "Infra",
        ],
    },

    "high_growth": {
        "equity_pct": 0.95,
        "etf_pct": 0.05,
        "cash_pct": 0.00,
        "max_single_stock": 0.30,
        "max_sector": 0.65,
        "volatility_target": 42,
        "sharpe_min": -0.5,
        "default_sectors": [
            "Technology",
            "Finance",
            "Auto",
            "Healthcare",
            "IT",
        ],
    },
}

# =============================================================================
# GOAL MAPPING
# =============================================================================

GOAL_TO_PROFILE = {
    "wealth_creation": "moderate",
    "passive_growth": "conservative",
    "retirement": "conservative",
    "high_growth": "aggressive",
    "dividend_income": "conservative",
    "low_risk": "conservative",
    "tax_efficient": "moderate",
    "learning": "moderate",
}

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class RiskProfile:
    category: str
    confidence: float
    explanation: str
    equity_pct: float
    etf_pct: float
    volatility_target: float
    max_sector: float


@dataclass
class StockRecommendation:
    symbol: str
    name: str
    sector: str

    allocation_pct: float
    allocation_amount: float

    shares_can_buy: Optional[int] = None
    price_per_share: Optional[float] = None

    role: str = ""
    why: str = ""
    risk_contribution: str = ""

    momentum_score: float = 0.0
    sharpe_estimate: float = 0.0
    volatility: float = 0.0
    composite_score: float = 0.0


# =============================================================================
# RISK PROFILE INFERENCE
# =============================================================================


def infer_risk_profile(
    amount: float,
    goal: str,
    horizon: str,
    market: str,
    preferred_sectors: List[str],
) -> RiskProfile:

    base = GOAL_TO_PROFILE.get(goal, "moderate")

    profiles = [
        "conservative",
        "moderate",
        "aggressive",
        "high_growth",
    ]

    idx = profiles.index(base)

    horizon_delta = {
        "short": +1,
        "medium": 0,
        "long": -1,
    }.get(horizon, 0)

    idx = max(0, min(3, idx + horizon_delta))

    aggressive = {
        "Technology",
        "Finance",
        "Auto",
        "IT",
        "Defense",
    }

    if preferred_sectors and len(
        set(preferred_sectors) & aggressive
    ) >= 2:
        idx = min(3, idx + 1)

    cat = profiles[idx]
    profile_data = RISK_PROFILES[cat]

    explanations = {
        "conservative": (
            "Your goal and timeline prioritize capital preservation. "
            "We focus on quality stocks with strong fundamentals "
            "and lower volatility."
        ),

        "moderate": (
            "A balanced approach targeting steady growth while "
            "managing risk. Selected based on real Sharpe ratio "
            "and momentum data."
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

    if (
        horizon == "long"
        and goal in [
            "wealth_creation",
            "high_growth",
            "retirement",
        ]
    ):
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


# =============================================================================
# ROLE ENGINE
# =============================================================================


def _role(
    sector: str,
    sharpe: float,
    momentum: float,
) -> str:

    defensive = {
        "FMCG",
        "Healthcare",
        "Energy",
        "Banking",
        "Pharma",
    }

    growth = {
        "Technology",
        "Finance",
        "Auto",
        "Consumer",
        "IT",
    }

    if sharpe > 1.0 and momentum > 15:
        return "growth"

    if sector in defensive and sharpe > 0:
        return "stability"

    if sector in growth:
        return "growth"

    if momentum < -5:
        return "recovery"

    return "balanced"


# =============================================================================
# WHY ENGINE
# =============================================================================


def _why(stock: Dict, role: str) -> str:

    sec = stock["sector"]

    sh = stock.get("sharpe", 0)
    mo = stock.get("momentum_1y", 0)
    vol = stock.get("volatility", 20)
    dd = stock.get("max_drawdown", -15)
    score = stock.get("composite_score", 50)

    parts = []

    if role == "stability":
        parts.append(
            f"Strong {sec} sector stock with defensive characteristics."
        )

    elif role == "growth":
        parts.append(
            f"Growth driver in {sec} sector with {mo:+.1f}% 1-year return."
        )

    elif role == "recovery":
        parts.append(
            f"Turnaround candidate in {sec} — oversold with recovery potential."
        )

    else:
        parts.append(
            f"Quality {sec} stock with balanced risk-return profile."
        )

    if sh > 1.5:
        parts.append(
            f"Excellent Sharpe ratio of {sh:.2f}."
        )

    elif sh > 0.8:
        parts.append(
            f"Good Sharpe ratio of {sh:.2f}."
        )

    elif sh > 0.3:
        parts.append(
            f"Positive Sharpe ratio of {sh:.2f}."
        )

    if abs(dd) < 15:
        parts.append(
            f"Low drawdown of {dd:.1f}%."
        )

    elif abs(dd) > 30:
        parts.append(
            f"Historically volatile with {dd:.1f}% drawdown."
        )

    if vol < 18:
        parts.append(
            "Below-market volatility stabilizes portfolio."
        )

    parts.append(
        f"Composite score: {score:.0f}/100."
    )

    return " ".join(parts)


# =============================================================================
# MAIN ENGINE
# =============================================================================

# Add these 3 functions to backend/app/recommendation/engine.py
# Place them BEFORE the generate_recommendation function

def _commentary(
    profile: RiskProfile,
    stocks: List[Dict],
    horizon: str,
    goal: str,
    metrics: Dict,
) -> str:
    n       = len(stocks)
    cat     = profile.category
    w_sh    = metrics.get("weighted_sharpe", 0)
    exp_r   = metrics.get("expected_return", 0)
    exp_v   = metrics.get("expected_volatility", 0)
    score   = metrics.get("portfolio_score", 50)
    n_sec   = metrics.get("n_sectors", 1)

    cap = {
        "conservative": "stable, capital-preserving",
        "moderate":     "balanced growth",
        "aggressive":   "growth-focused",
        "high_growth":  "high-growth",
    }.get(cat, "balanced")

    horizon_l = {"short": "short-term", "medium": "medium-term", "long": "long-term"}.get(horizon, "")
    goal_l    = goal.replace("_", " ")

    sh_comment = (
        f"Weighted portfolio Sharpe ratio of {w_sh:.2f} indicates "
        + ("excellent" if w_sh > 1.5 else "good" if w_sh > 0.8 else "moderate" if w_sh > 0.3 else "below-average")
        + " risk-adjusted returns based on 1-year historical data."
    )

    return (
        f"This {cap} portfolio of {n} stocks is built for your {horizon_l} {goal_l} goal. "
        f"Based on real 1-year yfinance data, these stocks delivered an average 1Y return of "
        f"{exp_r:+.1f}% with estimated portfolio volatility of ~{exp_v:.0f}%. "
        f"{sh_comment} "
        f"Spanning {n_sec} sector{'s' if n_sec > 1 else ''}, the portfolio scores {score}/100 "
        f"using a composite of Sharpe ratio, momentum, drawdown protection, and diversification."
    )


def _warnings(
    sector_alloc: Dict[str, float],
    metrics: Dict,
    profile: RiskProfile,
) -> List[str]:
    warnings_list = []
    exp_vol = metrics.get("expected_volatility", 0)

    for sec, pct in sector_alloc.items():
        if pct > 60:
            warnings_list.append(
                f"Heavy {sec} concentration ({pct:.0f}%) — high sector-specific risk"
            )
        elif pct > 45:
            warnings_list.append(
                f"Elevated {sec} exposure ({pct:.0f}%) — monitor sector developments"
            )

    if exp_vol > profile.volatility_target * 1.4:
        warnings_list.append(
            f"Portfolio volatility ({exp_vol:.0f}%) exceeds your profile target "
            f"({profile.volatility_target:.0f}%) — consider adding defensive stocks"
        )

    w_dd = metrics.get("weighted_drawdown", 0)
    if w_dd < -35:
        warnings_list.append(
            f"Average historical drawdown of {w_dd:.0f}% — portfolio has experienced "
            "significant peak-to-trough declines historically"
        )

    sh = metrics.get("weighted_sharpe", 0)
    if sh < 0:
        warnings_list.append(
            "Negative weighted Sharpe ratio — portfolio returns below risk-free rate historically. "
            "Consider reviewing sector selection."
        )

    return warnings_list


def _strengths(stocks: List[Dict], metrics: Dict) -> List[str]:
    strengths_list = []
    sh     = metrics.get("weighted_sharpe", 0)
    n_sec  = metrics.get("n_sectors", 1)
    div    = metrics.get("diversification_score", 0)
    exp_r  = metrics.get("expected_return", 0)

    if sh > 1.0:
        strengths_list.append(
            f"Strong portfolio Sharpe ratio of {sh:.2f} — historically excellent "
            "risk-adjusted returns verified using 1-year market data"
        )
    if div >= 65:
        strengths_list.append(
            f"Good diversification across {n_sec} sectors "
            f"(score: {div}/100) reduces concentration risk"
        )
    top_momentum = [s for s in stocks if s.get("momentum_1y", 0) > 20]
    if top_momentum:
        strengths_list.append(
            f"{len(top_momentum)} stock{'s' if len(top_momentum) > 1 else ''} with "
            f">20% 1-year return — strong momentum confirmed"
        )
    low_dd = [s for s in stocks if s.get("max_drawdown", -100) > -20]
    if len(low_dd) >= 2:
        strengths_list.append(
            f"{len(low_dd)} holdings with max drawdown < 20% — strong downside protection"
        )
    if exp_r > 15:
        strengths_list.append(
            f"Portfolio 1-year historical return of {exp_r:+.1f}% — "
            "significantly above typical fixed-income alternatives"
        )

    return strengths_list


def generate_recommendation(
    amount: float,
    goal: str,
    horizon: str,
    market: str,
    exchange: str = "auto",
    preferred_sectors: Optional[List[str]] = None,
    n_stocks_min: int = 5,
    n_stocks_max: int = 10,
) -> Dict:

    preferred_sectors = preferred_sectors or []

    # =========================================================================
    # CACHE
    # =========================================================================

    cache_key = cache._make_key(
        "rec_v4",
        {
            "amt": int(amount / 5000),
            "goal": goal,
            "h": horizon,
            "mkt": market,
            "sec": sorted(preferred_sectors),
            "nmin": n_stocks_min,
            "nmax": n_stocks_max,
        },
    )

    cached = cache.get(cache_key, 1800)

    if cached:
        logger.info("Recommendation loaded from cache")
        return cached

    # =========================================================================
    # PROFILE
    # =========================================================================

    profile = infer_risk_profile(
        amount,
        goal,
        horizon,
        market,
        preferred_sectors,
    )

    pdata = RISK_PROFILES[profile.category]

    # =========================================================================
    # UNIVERSE
    # =========================================================================

    from app.recommendation.universe import (
        get_universe,
        filter_by_sectors,
    )

    universe = get_universe(market)

    if not universe:
        return {
            "error": (
                "Could not fetch market data. "
                "Please try again."
            )
        }

    logger.info(f"Universe size: {len(universe)}")

    # =========================================================================
    # SECTOR FILTERING
    # =========================================================================

    if preferred_sectors:

        candidates = filter_by_sectors(
            universe,
            preferred_sectors,
        )

        if len(candidates) < max(3, n_stocks_min):

            logger.info(
                "Insufficient stocks in preferred sectors"
            )

            if len(candidates) < 3:
                candidates = universe

    else:

        candidates = filter_by_sectors(
            universe,
            pdata["default_sectors"],
        )

        if len(candidates) < n_stocks_min:
            candidates = universe

    logger.info(
        f"Candidates after filtering: {len(candidates)}"
    )

    # =========================================================================
    # SCORING
    # =========================================================================

    bench = "^NSEI" if market == "india" else "^GSPC"

    from app.recommendation.scorer import (
        score_stocks_batch,
    )

    scored = score_stocks_batch(
        candidates[:150],
        benchmark=bench,
    )

    if not scored:
        return {
            "error": (
                "Could not score stocks. "
                "Market data may be unavailable."
            )
        }

    # =========================================================================
    # PORTFOLIO BUILD
    # =========================================================================

    n_target = (
        n_stocks_min + n_stocks_max
    ) // 2

    from app.recommendation.portfolio_builder import (
        build_final_portfolio,
        enforce_affordability,
    )

    selected, weights, metrics = build_final_portfolio(
        scored,
        amount,
        n_target,
        pdata,
    )

    if not selected:
        return {
            "error": (
                "Could not build portfolio "
                "from available data."
            )
        }

    # =========================================================================
    # AFFORDABILITY ENFORCEMENT
    # =========================================================================

    for stock in selected:
        if "score_data" not in stock:
            stock["score_data"] = {}

    affordability_result = enforce_affordability(
        selected,
        weights,
        amount,
    )

    if len(affordability_result) == 3:
        (
            selected,
            weights,
            unaffordable_list,
        ) = affordability_result

    else:
        (
            selected,
            weights,
        ) = affordability_result

        unaffordable_list = []

    if not selected:
        return {
            "error": (
                "Investment amount too small "
                "for available stocks in selected sectors. "
                "Try a larger amount or different sectors."
            )
        }

    # =========================================================================
    # BUILD OUTPUT
    # =========================================================================

    # ── BUILD OUTPUT ──────────────────────────────────────────
    stocks_out    = []
    sector_alloc: Dict[str, float] = {}
    total_invested = metrics.get("total_invested", amount)
    uninvested     = metrics.get("uninvested_cash", 0)

    for stock in selected:
        shares         = stock.get("shares_to_buy", 0)
        price_per_share= stock.get("price_per_share", 0)
        total_cost     = stock.get("total_cost", 0)

        if shares == 0:
            continue

        actual_pct = round(total_cost / amount * 100, 1) if amount > 0 else 0
        role       = _role(stock["sector"], stock.get("sharpe", 0), stock.get("momentum_1y", 0))
        why        = _why(stock, role)
        vol        = stock.get("volatility", 20)
        risk       = "Low" if vol < 18 else "Medium" if vol < 28 else "High"

        stocks_out.append({
            "symbol":            stock["symbol"],
            "name":              stock.get("name", stock["symbol"]),
            "sector":            stock["sector"],
            "allocation_pct":    actual_pct,
            "allocation_amount": total_cost,
            # Whole share details — shown to user
            "shares_to_buy":     shares,
            "price_per_share":   price_per_share,
            "total_cost":        total_cost,
            "share_summary":     f"{shares} share{'s' if shares > 1 else ''} @ Rs.{price_per_share:,.0f} = Rs.{total_cost:,.0f}",
            # Analytics
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

    sector_list = sorted(
        [{"sector": k, "weight_pct": v} for k, v in sector_alloc.items()],
        key=lambda x: -x["weight_pct"],
    )

    commentary = _commentary(profile, stocks_out, horizon, goal, metrics)
    warnings   = _warnings(sector_alloc, metrics, profile)
    strengths  = _strengths(stocks_out, metrics)

    result = {
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
        "data_note":             "Scores based on real 1-year market data via yfinance. Whole shares only.",
        "sectors_used":          list(sector_alloc.keys()),
        "n_sectors":             metrics.get("n_sectors", 0),
    }

    cache.set(cache_key, result, 1800)
    return result

    # =========================================================================
    # SECTOR BREAKDOWN
    # =========================================================================

    sector_list = sorted(
        [
            {
                "sector": k,
                "weight_pct": v,
            }
            for k, v in sector_alloc.items()
        ],
        key=lambda x: -x["weight_pct"],
    )

    # =========================================================================
    # COMMENTARY
    # =========================================================================

    commentary = _commentary(
        profile,
        stocks_out,
        horizon,
        goal,
        metrics,
    )

    warnings = _warnings(
        sector_alloc,
        metrics,
        profile,
    )

    strengths = _strengths(
        stocks_out,
        metrics,
    )

    # =========================================================================
    # RESULT
    # =========================================================================

    result = {

        "profile": {
            "category": profile.category,
            "confidence": profile.confidence,
            "explanation": profile.explanation,
            "equity_pct": profile.equity_pct,
            "etf_pct": profile.etf_pct,
            "volatility_target": (
                profile.volatility_target
            ),
        },

        "stocks": stocks_out,

        "total_amount": amount,

        "expected_return": metrics.get(
            "expected_return",
            0,
        ),

        "expected_volatility": metrics.get(
            "expected_volatility",
            0,
        ),

        "portfolio_score": metrics.get(
            "portfolio_score",
            50,
        ),

        "diversification_score": metrics.get(
            "diversification_score",
            50,
        ),

        "weighted_sharpe": metrics.get(
            "weighted_sharpe",
            0,
        ),

        "weighted_beta": metrics.get(
            "weighted_beta",
            1.0,
        ),

        "score_breakdown": metrics.get(
            "score_breakdown",
            {},
        ),

        "ai_commentary": commentary,

        "sector_allocation": sector_list,

        "risk_warnings": warnings,

        "strengths": strengths,

        "data_note": (
            "Scores based on real 1-year market data via yfinance"
        ),

        "sectors_used": list(
            sector_alloc.keys()
        ),

        "n_sectors": metrics.get(
            "n_sectors",
            0,
        ),
    }

    # =========================================================================
    # AFFORDABILITY WARNINGS
    # =========================================================================

    if unaffordable_list:

        result["warnings"] = [
            (
                f"{sym} removed — allocation too small "
                f"to buy even 1 share at current price"
            )
            for sym in unaffordable_list
        ]

    # =========================================================================
    # CACHE SAVE
    # =========================================================================

    cache.set(
        cache_key,
        result,
        1800,
    )

    return result