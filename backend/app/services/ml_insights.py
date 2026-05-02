import numpy as np
from typing import List, Dict


def calculate_portfolio_score(
    holdings: List[Dict],
    risk_metrics: Dict
) -> Dict:
    """
    Generate a 0-100 portfolio health score using weighted ML-style scoring.
    No external API needed — pure math.
    """
    scores = {}

    # 1. Diversification score (0-25)
    n = len(holdings)
    sector_count = len(set(h.get("sector", "Unknown") for h in holdings))
    div_score = min(25, (min(n, 15) / 15) * 15 + (min(sector_count, 5) / 5) * 10)
    scores["diversification"] = round(div_score, 1)

    # 2. Risk-adjusted return score (0-25)
    sharpe = risk_metrics.get("sharpe_ratio", 0)
    sharpe_score = max(0, min(25, (sharpe + 1) / 3 * 25))
    scores["risk_adjusted_return"] = round(sharpe_score, 1)

    # 3. Volatility score (0-25) — lower volatility = higher score
    vol = risk_metrics.get("annualized_volatility_pct", 30)
    vol_score = max(0, min(25, (1 - (vol - 10) / 50) * 25))
    scores["volatility"] = round(vol_score, 1)

    # 4. Profit/Loss score (0-25)
    pnl_pcts = [h["pnl_pct"] for h in holdings if h.get("pnl_pct") is not None]
    if pnl_pcts:
        avg_pnl = np.mean(pnl_pcts)
        winners = sum(1 for p in pnl_pcts if p > 0)
        win_rate = winners / len(pnl_pcts)
        pnl_score = max(0, min(25, (avg_pnl / 50 + 0.5) * 12.5 + win_rate * 12.5))
    else:
        pnl_score = 12.5
    scores["profitability"] = round(pnl_score, 1)

    total_score = round(sum(scores.values()), 1)

    # Grade
    if total_score >= 80:
        grade, grade_color, grade_label = "A", "text-green-400", "Excellent"
    elif total_score >= 65:
        grade, grade_color, grade_label = "B", "text-blue-400", "Good"
    elif total_score >= 50:
        grade, grade_color, grade_label = "C", "text-yellow-400", "Average"
    elif total_score >= 35:
        grade, grade_color, grade_label = "D", "text-orange-400", "Below Average"
    else:
        grade, grade_color, grade_label = "F", "text-red-400", "Poor"

    return {
        "total_score": total_score,
        "grade": grade,
        "grade_color": grade_color,
        "grade_label": grade_label,
        "breakdown": scores
    }


def detect_correlated_stocks(holdings: List[Dict]) -> List[Dict]:
    """
    Detect which stocks in the portfolio are likely correlated
    based on sector — no historical data needed.
    """
    sector_groups: Dict[str, List[str]] = {}
    for h in holdings:
        sector = h.get("sector") or "Unknown"
        sector_groups.setdefault(sector, []).append(h["symbol"])

    warnings = []
    for sector, symbols in sector_groups.items():
        if len(symbols) >= 3:
            warnings.append({
                "sector": sector,
                "symbols": symbols,
                "message": f"{', '.join(symbols)} are all in {sector} and likely move together — this multiplies sector risk."
            })

    return warnings