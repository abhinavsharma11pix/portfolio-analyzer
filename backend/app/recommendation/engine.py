"""
AI-powered portfolio recommendation engine.
Uses free data sources only: yfinance + static curated universe.
"""
import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from app.cache import store as cache

logger = logging.getLogger(__name__)

INDIA_UNIVERSE = {
    "Large Cap": {
        "Technology":  ["INFY.NS","TCS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
        "Banking":     ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","SBIN.NS","AXISBANK.NS"],
        "FMCG":        ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS"],
        "Energy":      ["RELIANCE.NS","ONGC.NS","BPCL.NS","NTPC.NS","POWERGRID.NS"],
        "Healthcare":  ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","APOLLOHOSP.NS"],
        "Auto":        ["MARUTI.NS","M&M.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS","EICHERMOT.NS"],
        "Infra":       ["LT.NS","ADANIPORTS.NS","ULTRACEMCO.NS","GRASIM.NS","SHREECEM.NS"],
        "Finance":     ["BAJFINANCE.NS","BAJAJFINSV.NS","MUTHOOTFIN.NS","CHOLAFIN.NS","SBILIFE.NS"],
        "Consumer":    ["ASIANPAINT.NS","TITAN.NS","PIDILITIND.NS","HAVELLS.NS","VOLTAS.NS"],
        "Pharma":      ["LUPIN.NS","AUROPHARMA.NS","TORNTPHARM.NS","ALKEM.NS","GLENMARK.NS"],
    },
    "ETF": {
        "Index": ["NIFTYBEES.NS","SETFNIF50.NS","JUNIORBEES.NS"],
        "Gold":  ["GOLDBEES.NS"],
        "Sector":["BANKBEES.NS","ITBEES.NS"],
    },
}

US_UNIVERSE = {
    "Technology": ["AAPL","MSFT","GOOGL","NVDA","META","AMD","INTC"],
    "Finance":    ["JPM","BAC","GS","MS","V","MA"],
    "Healthcare": ["JNJ","PFE","ABBV","MRK","UNH"],
    "Consumer":   ["AMZN","TSLA","NKE","SBUX","MCD"],
    "Energy":     ["XOM","CVX","COP","SLB"],
    "ETF":        ["SPY","QQQ","VTI","ARKK","GLD"],
}

RISK_PROFILES = {
    "conservative": {
        "equity_pct": 0.40, "etf_pct": 0.40, "cash_pct": 0.20,
        "max_sector_conc": 0.30, "preferred_cap": "Large Cap",
        "preferred_sectors": ["FMCG","Banking","Healthcare","Energy"],
        "volatility_target": 12,
    },
    "moderate": {
        "equity_pct": 0.70, "etf_pct": 0.20, "cash_pct": 0.10,
        "max_sector_conc": 0.40, "preferred_cap": "Large Cap",
        "preferred_sectors": ["Technology","Banking","Healthcare","Finance","Consumer"],
        "volatility_target": 20,
    },
    "aggressive": {
        "equity_pct": 0.85, "etf_pct": 0.10, "cash_pct": 0.05,
        "max_sector_conc": 0.50, "preferred_cap": "Large Cap",
        "preferred_sectors": ["Technology","Finance","Auto","Consumer","Infra"],
        "volatility_target": 28,
    },
    "high_growth": {
        "equity_pct": 0.95, "etf_pct": 0.05, "cash_pct": 0.00,
        "max_sector_conc": 0.60, "preferred_cap": "Large Cap",
        "preferred_sectors": ["Technology","Finance","Auto","Healthcare"],
        "volatility_target": 35,
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

HORIZON_MULTIPLIER = {
    "short":  {"return_weight": 0.6, "safety_weight": 0.4},
    "medium": {"return_weight": 0.5, "safety_weight": 0.5},
    "long":   {"return_weight": 0.4, "safety_weight": 0.6},
}


@dataclass
class RiskProfile:
    category:          str
    confidence:        float
    explanation:       str
    equity_pct:        float
    etf_pct:           float
    volatility_target: float


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
    momentum_score:    float = 0.0
    sharpe_estimate:   float = 0.0


@dataclass
class PortfolioRecommendation:
    profile:                RiskProfile
    stocks:                 List[StockRecommendation]
    total_amount:           float
    expected_volatility:    float
    diversification_score:  int
    portfolio_score:        int
    ai_commentary:          str
    sector_allocation:      List[Dict]
    risk_warnings:          List[str]
    strengths:              List[str]
    alternative_portfolios: Dict = field(default_factory=dict)


def infer_risk_profile(
    amount: float,
    goal: str,
    horizon: str,
    market: str,
    preferred_sectors: List[str],
) -> RiskProfile:
    base     = GOAL_TO_PROFILE.get(goal, "moderate")
    profiles = ["conservative", "moderate", "aggressive", "high_growth"]
    base_idx = profiles.index(base)

    horizon_adj = {"short": 1, "medium": 0, "long": -1}.get(horizon, 0)
    adj_idx     = max(0, min(3, base_idx + horizon_adj))
    adjusted    = profiles[adj_idx]

    aggressive_sectors = {"Technology", "Finance", "Crypto", "Auto"}
    if preferred_sectors:
        overlap = len(set(preferred_sectors) & aggressive_sectors)
        if overlap >= 2 and adj_idx < 3:
            adj_idx  = min(3, adj_idx + 1)
            adjusted = profiles[adj_idx]

    if amount < 10000 and goal == "learning":
        adjusted = "moderate"

    profile_data = RISK_PROFILES[adjusted]
    explanations = {
        "conservative": "Based on your goal and timeline, capital preservation takes priority. We focus on stable, dividend-paying stocks and ETFs.",
        "moderate":     "Your inputs suggest a balanced approach — steady growth while managing downside risk through diversification.",
        "aggressive":   "Your goal and horizon indicate higher growth tolerance. We lean towards growth-oriented stocks with calculated risk.",
        "high_growth":  "Maximum growth orientation detected. This portfolio targets superior returns with higher volatility.",
    }

    confidence = 0.75
    if horizon == "long" and goal in ["wealth_creation", "high_growth"]:
        confidence = 0.90
    if horizon == "short" and goal == "low_risk":
        confidence = 0.95

    return RiskProfile(
        category=adjusted,
        confidence=confidence,
        explanation=explanations[adjusted],
        equity_pct=profile_data["equity_pct"],
        etf_pct=profile_data["etf_pct"],
        volatility_target=profile_data["volatility_target"],
    )


def _score_stock(symbol: str, period: str = "6mo") -> Dict:
    key    = f"stock_score:{symbol}"
    cached = cache.get(key, 3600, disk=True)
    if cached:
        return cached

    try:
        t    = yf.Ticker(symbol)
        hist = t.history(period=period, timeout=8)
        if hist.empty or len(hist) < 20:
            return {"momentum": 0.5, "sharpe": 0.5, "volatility": 20.0, "raw_return": 0.0, "valid": False}

        close  = hist["Close"]
        ret    = close.pct_change().dropna()
        mom    = float((close.iloc[-1] / close.iloc[0] - 1) * 100)
        vol    = float(ret.std() * np.sqrt(252) * 100)
        rf     = 0.065 / 252
        sharpe = float((ret.mean() - rf) / ret.std() * np.sqrt(252)) if ret.std() > 0 else 0.0

        mom_norm = min(1.0, max(0.0, (mom + 50) / 100))

        result = {
            "momentum":   round(mom_norm, 3),
            "sharpe":     round(min(3.0, max(-1.0, sharpe)), 3),
            "volatility": round(vol, 1),
            "raw_return": round(mom, 2),
            "valid":      True,
        }
        cache.set(key, result, 3600, disk=True)
        return result
    except Exception:
        return {"momentum": 0.5, "sharpe": 0.5, "volatility": 20.0, "raw_return": 0.0, "valid": False}


def _get_company_name(symbol: str) -> str:
    key    = f"name:{symbol}"
    cached = cache.get(key, 86400, disk=True)
    if cached:
        return cached
    try:
        info = yf.Ticker(symbol).info
        name = info.get("longName") or info.get("shortName") or symbol.replace(".NS","").replace(".BO","")
        cache.set(key, name, 86400, disk=True)
        return name
    except Exception:
        return symbol.replace(".NS","").replace(".BO","")


def _select_stocks(
    market: str,
    profile: RiskProfile,
    preferred_sectors: List[str],
    n_stocks: int = 8,
) -> List[Dict]:
    universe = INDIA_UNIVERSE["Large Cap"] if market == "india" else US_UNIVERSE
    pref_profile  = RISK_PROFILES[profile.category]
    pref_sectors  = preferred_sectors or pref_profile["preferred_sectors"]

    candidates: List[Dict] = []
    seen: set = set()

    for sector in pref_sectors:
        syms = universe.get(sector, [])
        for sym in syms[:3]:
            if sym not in seen:
                candidates.append({"symbol": sym, "sector": sector, "priority": 1})
                seen.add(sym)

    for sector, syms in universe.items():
        if len(candidates) >= n_stocks * 2:
            break
        for sym in syms[:2]:
            if sym not in seen:
                candidates.append({"symbol": sym, "sector": sector, "priority": 2})
                seen.add(sym)

    scored = []
    for c in candidates[:n_stocks * 3]:
        score = _score_stock(c["symbol"])
        c["score_data"] = score
        combined = (
            score["momentum"] * 0.4
            + min(1.0, max(0.0, score["sharpe"] / 3)) * 0.4
            + (1 - min(1.0, score["volatility"] / 50)) * 0.2
        )
        c["combined_score"] = combined
        scored.append(c)

    scored.sort(key=lambda x: -x["combined_score"])
    return scored[:n_stocks]


def _allocate_weights(
    stocks: List[Dict],
    profile: RiskProfile,
    horizon: str,
) -> List[float]:
    vols    = np.array([max(1.0, s["score_data"].get("volatility", 20.0)) for s in stocks])
    inv_vol = 1.0 / vols
    weights = inv_vol / inv_vol.sum()

    max_w   = RISK_PROFILES[profile.category]["max_sector_conc"]
    weights = np.minimum(weights, max_w)
    weights = weights / weights.sum()

    return weights.tolist()


def _role_for_stock(sector: str, profile_cat: str) -> str:
    stable   = {"FMCG", "Healthcare", "Energy", "Banking"}
    growth   = {"Technology", "Finance", "Auto", "Consumer"}
    dividend = {"FMCG", "Energy", "Infra"}
    if sector in dividend and profile_cat == "conservative":
        return "dividend"
    if sector in stable:
        return "stability"
    if sector in growth:
        return "growth"
    return "balanced"


def _why_selected(symbol: str, sector: str, score: Dict, role: str) -> str:
    mom   = score.get("raw_return", 0.0)
    sh    = score.get("sharpe", 0.0)
    vol   = score.get("volatility", 20.0)
    lines = []

    if role == "stability":
        lines.append(f"Selected for portfolio stability — {sector} sector provides defensive characteristics.")
    elif role == "growth":
        lines.append(f"Growth driver — {sector} exposure with {mom:+.1f}% recent momentum.")
    elif role == "dividend":
        lines.append(f"Income generator — historically strong dividend yield from {sector} sector.")
    else:
        lines.append(f"Balanced contributor across {sector} sector fundamentals.")

    if sh > 1.5:
        lines.append(f"Excellent risk-adjusted returns (Sharpe: {sh:.1f}).")
    elif sh > 0.5:
        lines.append(f"Solid risk-adjusted performance (Sharpe: {sh:.1f}).")

    if vol < 18:
        lines.append("Lower volatility than market average — stabilizes portfolio.")
    elif vol > 30:
        lines.append("Higher volatility — positions sized conservatively.")

    return " ".join(lines)


def generate_recommendation(
    amount: float,
    goal: str,
    horizon: str,
    market: str,
    exchange: str = "auto",
    preferred_sectors: Optional[List[str]] = None,
) -> Dict:
    preferred_sectors = preferred_sectors or []

    # 1. Risk profiling
    profile = infer_risk_profile(amount, goal, horizon, market, preferred_sectors)

    # 2. Select stocks
    n_stocks = 6 if profile.category == "conservative" else 8 if profile.category == "moderate" else 10
    selected = _select_stocks(market, profile, preferred_sectors, n_stocks)

    if not selected:
        return {"error": "Could not fetch market data. Please try again."}

    # 3. Allocate weights
    weights = _allocate_weights(selected, profile, horizon)

    # 4. Build recommendations
    stocks: List[StockRecommendation] = []
    sector_alloc: Dict[str, float]    = {}

    for stock, weight in zip(selected, weights):
        score         = stock["score_data"]
        sector        = stock["sector"]
        role          = _role_for_stock(sector, profile.category)
        alloc_amount  = round(amount * weight, 2)
        name          = _get_company_name(stock["symbol"])

        stocks.append(StockRecommendation(
            symbol=stock["symbol"],
            name=name,
            sector=sector,
            allocation_pct=round(weight * 100, 1),
            allocation_amount=alloc_amount,
            role=role,
            why=_why_selected(stock["symbol"], sector, score, role),
            risk_contribution=(
                "Low"    if score.get("volatility", 20) < 18
                else "Medium" if score.get("volatility", 20) < 28
                else "High"
            ),
            momentum_score=score.get("momentum", 0.5),
            sharpe_estimate=score.get("sharpe", 0.5),
        ))
        sector_alloc[sector] = sector_alloc.get(sector, 0) + weight * 100

    # 5. Portfolio metrics
    vols    = np.array([s["score_data"].get("volatility", 20) for s in selected])
    w       = np.array(weights)
    exp_vol = float(np.sqrt(w @ np.diag(vols ** 2) @ w))

    n_sectors  = len(sector_alloc)
    max_conc   = max(sector_alloc.values())
    div_score  = min(100, int(
        (min(len(stocks), 12) / 12 * 40)
        + (min(n_sectors, 8) / 8 * 30)
        + ((100 - max_conc) * 0.30)
    ))
    port_score = min(100, int(div_score * 0.4 + min(100, (3 - max(0, 3 - exp_vol / 10)) * 20) * 0.6))

    # 6. AI commentary
    commentary = _generate_commentary(profile, stocks, horizon, goal, exp_vol, div_score)

    # 7. Warnings and strengths
    warnings  = _generate_warnings(sector_alloc, exp_vol, profile)
    strengths = _generate_strengths(stocks, div_score, n_sectors)

    # 8. Sector allocation list
    sector_list = sorted(
        [{"sector": k, "weight_pct": round(v, 1)} for k, v in sector_alloc.items()],
        key=lambda x: -x["weight_pct"],
    )

    result = PortfolioRecommendation(
        profile=profile,
        stocks=stocks,
        total_amount=amount,
        expected_volatility=round(exp_vol, 1),
        diversification_score=div_score,
        portfolio_score=port_score,
        ai_commentary=commentary,
        sector_allocation=sector_list,
        risk_warnings=warnings,
        strengths=strengths,
    )

    return _serialize(result)


def _generate_commentary(
    profile: RiskProfile,
    stocks: List[StockRecommendation],
    horizon: str,
    goal: str,
    vol: float,
    div_score: int,
) -> str:
    cap_name = {
        "conservative": "stable",
        "moderate":     "balanced",
        "aggressive":   "growth-oriented",
        "high_growth":  "high-conviction growth",
    }
    horizon_label = {"short": "short", "medium": "medium", "long": "long-term"}.get(horizon, "medium")
    goal_label    = goal.replace("_", " ")
    div_comment   = "excellent spread across sectors" if div_score >= 70 else "consider adding more sectors for better balance"

    return (
        f"This {cap_name.get(profile.category, 'balanced')} portfolio of {len(stocks)} stocks "
        f"is designed for your {horizon_label} {goal_label} goal. "
        f"Expected annual volatility of ~{vol:.0f}% aligns with your {profile.category} risk profile. "
        f"The portfolio scores {div_score}/100 on diversification — {div_comment}. "
        f"{'Focus on compounding returns over time.' if horizon == 'long' else 'Monitor market conditions closely given the shorter horizon.'}"
    )


def _generate_warnings(
    sector_alloc: Dict[str, float],
    vol: float,
    profile: RiskProfile,
) -> List[str]:
    warnings = []
    for sec, pct in sector_alloc.items():
        if pct > 50:
            warnings.append(f"High {sec} concentration ({pct:.0f}%) — sector-specific risk elevated")
    if vol > profile.volatility_target * 1.3:
        warnings.append(f"Portfolio volatility ({vol:.0f}%) exceeds target — consider adding defensive positions")
    if vol > 35:
        warnings.append("High overall volatility — suitable only for investors comfortable with significant price swings")
    return warnings


def _generate_strengths(
    stocks: List[StockRecommendation],
    div_score: int,
    n_sectors: int,
) -> List[str]:
    strengths = []
    if div_score >= 70:
        strengths.append(f"Excellent diversification across {n_sectors} sectors reduces single-sector risk")
    high_sharpe = [s for s in stocks if s.sharpe_estimate > 1.0]
    if high_sharpe:
        strengths.append(f"{len(high_sharpe)} stocks with Sharpe > 1.0 — strong risk-adjusted return history")
    stable = [s for s in stocks if s.role in ["stability", "dividend"]]
    if len(stable) >= 2:
        strengths.append(f"{len(stable)} defensive holdings provide portfolio stability")
    return strengths


def _serialize(rec: PortfolioRecommendation) -> Dict:
    return {
        "profile":               asdict(rec.profile),
        "stocks":                [asdict(s) for s in rec.stocks],
        "total_amount":          rec.total_amount,
        "expected_volatility":   rec.expected_volatility,
        "diversification_score": rec.diversification_score,
        "portfolio_score":       rec.portfolio_score,
        "ai_commentary":         rec.ai_commentary,
        "sector_allocation":     rec.sector_allocation,
        "risk_warnings":         rec.risk_warnings,
        "strengths":             rec.strengths,
    }