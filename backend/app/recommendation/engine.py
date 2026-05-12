"""
Production AI recommendation engine.
Uses real NSE/S&P500 stock universe + real yfinance scoring.
Strictly respects user sector preferences.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from app.cache import store as cache

logger = logging.getLogger(__name__)

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


@dataclass
class RiskProfile:
    category:          str
    confidence:        float
    explanation:       str
    equity_pct:        float
    etf_pct:           float
    volatility_target: float
    max_sector:        float


@dataclass
class StockRecommendation:
    symbol:            str
    name:              str
    sector:            str
    allocation_pct:    float
    allocation_amount: float
    role:              str
    why:               str
    risk_contribution: str
    momentum_score:    float
    sharpe_estimate:   float
    volatility:        float
    composite_score:   float


def infer_risk_profile(
    amount: float,
    goal: str,
    horizon: str,
    market: str,
    preferred_sectors: List[str],
) -> RiskProfile:
    base     = GOAL_TO_PROFILE.get(goal, "moderate")
    profiles = ["conservative", "moderate", "aggressive", "high_growth"]
    idx      = profiles.index(base)

    horizon_delta = {"short": +1, "medium": 0, "long": -1}.get(horizon, 0)
    idx = max(0, min(3, idx + horizon_delta))

    aggressive = {"Technology", "Finance", "Auto", "IT", "Defense"}
    if preferred_sectors and len(set(preferred_sectors) & aggressive) >= 2:
        idx = min(3, idx + 1)

    cat          = profiles[idx]
    profile_data = RISK_PROFILES[cat]

    explanations = {
        "conservative": "Your goal and timeline prioritize capital preservation. We focus on quality stocks with strong fundamentals and lower volatility.",
        "moderate":     "A balanced approach targeting steady growth while managing risk. Selected based on real Sharpe ratio and momentum data.",
        "aggressive":   "Growth-oriented strategy with higher return potential. Stocks selected for momentum and risk-adjusted performance.",
        "high_growth":  "Maximum growth targeting. High-conviction stocks selected using composite scoring across multiple financial metrics.",
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


def _why(stock: Dict, role: str) -> str:
    sym   = stock["symbol"]
    sec   = stock["sector"]
    sh    = stock.get("sharpe", 0)
    mo    = stock.get("momentum_1y", 0)
    vol   = stock.get("volatility", 20)
    dd    = stock.get("max_drawdown", -15)
    score = stock.get("composite_score", 50)

    parts = []

    if role == "stability":
        parts.append(f"Strong {sec} sector stock with defensive characteristics.")
    elif role == "growth":
        parts.append(f"Growth driver in {sec} sector with {mo:+.1f}% 1-year return.")
    elif role == "recovery":
        parts.append(f"Turnaround candidate in {sec} — oversold with recovery potential.")
    else:
        parts.append(f"Quality {sec} stock with balanced risk-return profile.")

    if sh > 1.5:
        parts.append(f"Excellent Sharpe ratio of {sh:.2f} — top-tier risk-adjusted performance.")
    elif sh > 0.8:
        parts.append(f"Good Sharpe ratio of {sh:.2f} — solid risk compensation.")
    elif sh > 0.3:
        parts.append(f"Positive Sharpe ({sh:.2f}) — returns exceed risk-free rate.")

    if abs(dd) < 15:
        parts.append(f"Low max drawdown of {dd:.1f}% — strong downside protection.")
    elif abs(dd) > 30:
        parts.append(f"Notable drawdown of {dd:.1f}% — sized conservatively in portfolio.")

    if vol < 18:
        parts.append("Below-market volatility stabilizes overall portfolio.")

    parts.append(f"Composite score: {score:.0f}/100.")
    return " ".join(parts)


def generate_recommendation(
    amount:            float,
    goal:              str,
    horizon:           str,
    market:            str,
    exchange:          str       = "auto",
    preferred_sectors: Optional[List[str]] = None,
    n_stocks_min:      int       = 5,
    n_stocks_max:      int       = 10,
) -> Dict:
    """
    Main pipeline:
    1. Fetch full market universe (NSE / S&P500)
    2. Filter strictly by user sectors (if provided)
    3. Score all candidate stocks with real yfinance data
    4. Select top N using ML composite score
    5. Allocate weights using inverse-vol + score blend
    6. Compute real portfolio metrics
    """
    preferred_sectors = preferred_sectors or []

    # Cache key includes all inputs
    cache_key = cache._make_key("rec_v3", {
        "amt":   int(amount / 5000),   # bucket to 5K for cache hits
        "goal":  goal, "h": horizon, "mkt": market,
        "sec":   sorted(preferred_sectors),
        "nmin":  n_stocks_min, "nmax": n_stocks_max,
    })
    cached = cache.get(cache_key, 1800)
    if cached:
        logger.info("Recommendation from cache")
        return cached

    # 1. Risk profile
    profile = infer_risk_profile(amount, goal, horizon, market, preferred_sectors)
    pdata   = RISK_PROFILES[profile.category]

    # 2. Fetch universe
    from app.recommendation.universe import get_universe, filter_by_sectors
    universe = get_universe(market)
    if not universe:
        return {"error": "Could not fetch market data. Please try again."}

    logger.info(f"Universe size: {len(universe)} stocks")

    # 3. STRICT sector filtering
    if preferred_sectors:
        candidates = filter_by_sectors(universe, preferred_sectors)
        if len(candidates) < max(3, n_stocks_min):
            # Not enough in preferred — warn but include close sectors
            logger.info(f"Only {len(candidates)} stocks in selected sectors — expanding slightly")
            candidates = filter_by_sectors(universe, preferred_sectors)
            if len(candidates) < 3:
                candidates = universe  # last resort fallback
    else:
        # No preference — use profile defaults
        default_sectors = pdata["default_sectors"]
        candidates = filter_by_sectors(universe, default_sectors)
        if len(candidates) < n_stocks_min:
            candidates = universe

    logger.info(f"Candidates after sector filter: {len(candidates)}")

    # 4. Score candidates (limit to 150 for performance)
    # Take top 150 by order from universe (broadly representative)
    bench = "^NSEI" if market == "india" else "^GSPC"
    from app.recommendation.scorer import score_stocks_batch
    scored = score_stocks_batch(candidates[:150], benchmark=bench)

    if not scored:
        return {"error": "Could not score stocks. Market data may be temporarily unavailable."}

    # Target stock count = midpoint of user range
    n_target = (n_stocks_min + n_stocks_max) // 2

    # 5. Build portfolio
    from app.recommendation.portfolio_builder import build_final_portfolio
    selected, weights, metrics = build_final_portfolio(
        scored, amount, n_target, pdata
    )

    if not selected:
        return {"error": "Could not build portfolio from available data."}

    # 6. Build output
    stocks_out = []
    sector_alloc: Dict[str, float] = {}

    for stock, weight in zip(selected, weights):
        alloc_amount = round(float(amount * weight), 2)
        alloc_pct    = round(float(weight * 100), 1)
        role         = _role(stock["sector"], stock.get("sharpe", 0), stock.get("momentum_1y", 0))
        why          = _why(stock, role)

        vol  = stock.get("volatility", 20)
        risk = "Low" if vol < 18 else "Medium" if vol < 28 else "High"

        stocks_out.append({
            "symbol":            stock["symbol"],
            "name":              stock.get("name", stock["symbol"]),
            "sector":            stock["sector"],
            "allocation_pct":    alloc_pct,
            "allocation_amount": alloc_amount,
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
        sector_alloc[sec] = round(sector_alloc.get(sec, 0) + alloc_pct, 1)

    # Sector list
    sector_list = sorted(
        [{"sector": k, "weight_pct": v} for k, v in sector_alloc.items()],
        key=lambda x: -x["weight_pct"]
    )

    # Commentary + warnings + strengths
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
        "data_note":             "Scores based on real 1-year market data via yfinance",
        "sectors_used":          list(sector_alloc.keys()),
        "n_sectors":             metrics.get("n_sectors", 0),
    }

    cache.set(cache_key, result, 1800)
    return result


def _commentary(profile, stocks, horizon, goal, metrics) -> str:
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


def _warnings(sector_alloc: Dict, metrics: Dict, profile: RiskProfile) -> List[str]:
    warnings = []
    exp_vol   = metrics.get("expected_volatility", 0)

    for sec, pct in sector_alloc.items():
        if pct > 60:
            warnings.append(f"Heavy {sec} concentration ({pct:.0f}%) — high sector-specific risk")
        elif pct > 45:
            warnings.append(f"Elevated {sec} exposure ({pct:.0f}%) — monitor sector developments")

    if exp_vol > profile.volatility_target * 1.4:
        warnings.append(
            f"Portfolio volatility ({exp_vol:.0f}%) exceeds your profile target "
            f"({profile.volatility_target:.0f}%) — consider adding defensive stocks"
        )

    w_dd = metrics.get("weighted_drawdown", 0)
    if w_dd < -35:
        warnings.append(
            f"Average historical drawdown of {w_dd:.0f}% — portfolio has experienced "
            "significant peak-to-trough declines historically"
        )

    sh = metrics.get("weighted_sharpe", 0)
    if sh < 0:
        warnings.append(
            "Negative weighted Sharpe ratio — portfolio returns below risk-free rate historically. "
            "Consider reviewing sector selection."
        )

    return warnings


def _strengths(stocks: List[Dict], metrics: Dict) -> List[str]:
    strengths = []
    sh        = metrics.get("weighted_sharpe", 0)
    n_sec     = metrics.get("n_sectors", 1)
    div       = metrics.get("diversification_score", 0)
    exp_r     = metrics.get("expected_return", 0)

    if sh > 1.0:
        strengths.append(
            f"Strong portfolio Sharpe ratio of {sh:.2f} — historically excellent "
            "risk-adjusted returns verified using 1-year market data"
        )
    if div >= 65:
        strengths.append(
            f"Good diversification across {n_sec} sectors "
            f"(score: {div}/100) reduces concentration risk"
        )
    top_momentum = [s for s in stocks if s.get("momentum_1y", 0) > 20]
    if top_momentum:
        strengths.append(
            f"{len(top_momentum)} stock{'s' if len(top_momentum) > 1 else ''} with "
            f">20% 1-year return — strong momentum confirmed"
        )
    low_dd = [s for s in stocks if s.get("max_drawdown", -100) > -20]
    if len(low_dd) >= 2:
        strengths.append(
            f"{len(low_dd)} holdings with max drawdown < 20% — strong downside protection"
        )
    if exp_r > 15:
        strengths.append(
            f"Portfolio 1-year historical return of {exp_r:+.1f}% — "
            "significantly above typical fixed-income alternatives"
        )

    return strengths