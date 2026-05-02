from typing import List, Dict, Any

def generate_rule_insights(
    holdings: List[Dict],
    summary: Dict,
    risk_metrics: Dict
) -> List[Dict]:
    """
    Generate insights using pure logic — no API, no cost, instant.
    Returns list of insight objects with type, severity, message.
    """
    insights = []

    # ── Sector Concentration ──────────────────────────────────────
    sector_values: Dict[str, float] = {}
    total_value = sum(h.get("current_value") or h.get("invested_value", 0) for h in holdings)

    for h in holdings:
        sector = h.get("sector") or "Unknown"
        val = h.get("current_value") or h.get("invested_value", 0)
        sector_values[sector] = sector_values.get(sector, 0) + val

    for sector, val in sector_values.items():
        pct = (val / total_value * 100) if total_value else 0
        if pct > 50:
            insights.append({
                "type": "concentration_risk",
                "severity": "high",
                "icon": "⚠️",
                "title": f"Heavy {sector} Concentration",
                "message": f"{pct:.1f}% of your portfolio is in {sector}. A single sector event could significantly impact your returns.",
                "action": f"Consider reducing {sector} exposure below 40% by diversifying into other sectors."
            })
        elif pct > 35:
            insights.append({
                "type": "concentration_risk",
                "severity": "medium",
                "icon": "🔶",
                "title": f"High {sector} Exposure",
                "message": f"{sector} makes up {pct:.1f}% of your portfolio.",
                "action": "Consider slight diversification to reduce sector risk."
            })

    # ── Number of Holdings ────────────────────────────────────────
    n = len(holdings)
    if n < 5:
        insights.append({
            "type": "diversification",
            "severity": "high",
            "icon": "⚠️",
            "title": "Under-Diversified Portfolio",
            "message": f"You only hold {n} stocks. This increases individual stock risk significantly.",
            "action": "Consider expanding to 10-15 stocks across different sectors."
        })
    elif n > 30:
        insights.append({
            "type": "diversification",
            "severity": "low",
            "icon": "ℹ️",
            "title": "Over-Diversified Portfolio",
            "message": f"With {n} stocks, tracking performance becomes difficult and dilutes returns.",
            "action": "Consider trimming to your highest-conviction 15-20 positions."
        })

    # ── Individual Stock Losers ───────────────────────────────────
    big_losers = [h for h in holdings if h.get("pnl_pct") is not None and h["pnl_pct"] < -30]
    for h in big_losers:
        insights.append({
            "type": "loss_alert",
            "severity": "high",
            "icon": "🔴",
            "title": f"{h['symbol']} Down {abs(h['pnl_pct']):.1f}%",
            "message": f"{h['symbol']} has lost {abs(h['pnl_pct']):.1f}% from your buy price.",
            "action": "Review the fundamental thesis. If unchanged, consider averaging down or cutting losses."
        })

    # ── Big Winners ───────────────────────────────────────────────
    big_winners = [h for h in holdings if h.get("pnl_pct") is not None and h["pnl_pct"] > 50]
    for h in big_winners:
        insights.append({
            "type": "profit_alert",
            "severity": "low",
            "icon": "🟢",
            "title": f"{h['symbol']} Up {h['pnl_pct']:.1f}%",
            "message": f"{h['symbol']} has gained {h['pnl_pct']:.1f}% — a strong performer.",
            "action": "Consider booking partial profits to lock in gains and rebalance."
        })

    # ── Sharpe Ratio ──────────────────────────────────────────────
    sharpe = risk_metrics.get("sharpe_ratio", 0)
    if sharpe < 0:
        insights.append({
            "type": "risk_metric",
            "severity": "high",
            "icon": "📉",
            "title": "Negative Risk-Adjusted Return",
            "message": f"Your Sharpe ratio is {sharpe:.2f}. You're taking risk without adequate compensation.",
            "action": "Review underperforming positions. A fixed deposit would currently outperform this portfolio on risk-adjusted basis."
        })
    elif sharpe > 2:
        insights.append({
            "type": "risk_metric",
            "severity": "low",
            "icon": "🏆",
            "title": "Excellent Risk-Adjusted Returns",
            "message": f"Sharpe ratio of {sharpe:.2f} is outstanding. Your portfolio is generating strong returns per unit of risk.",
            "action": "Maintain current allocation. Document your strategy."
        })

    # ── Volatility Alert ──────────────────────────────────────────
    vol = risk_metrics.get("annualized_volatility_pct", 0)
    if vol > 35:
        insights.append({
            "type": "volatility",
            "severity": "high",
            "icon": "🌊",
            "title": "High Portfolio Volatility",
            "message": f"Annual volatility of {vol:.1f}% means your portfolio could swing ±{vol/2:.0f}% in a year.",
            "action": "Add defensive stocks (FMCG, Pharma) or debt instruments to reduce volatility."
        })

    # ── Drawdown Alert ────────────────────────────────────────────
    drawdown = risk_metrics.get("max_drawdown_pct", 0)
    if drawdown < -35:
        insights.append({
            "type": "drawdown",
            "severity": "high",
            "icon": "📊",
            "title": "Severe Historical Drawdown",
            "message": f"Your portfolio has experienced a maximum drawdown of {drawdown:.1f}%.",
            "action": "Consider stop-loss strategies and position sizing rules to limit future drawdowns."
        })

    # ── Missing Sector Diversification ────────────────────────────
    sectors_present = set(sector_values.keys()) - {"Unknown"}
    recommended = {"Technology", "Banking", "Energy", "Healthcare", "FMCG"}
    missing = recommended - sectors_present
    if len(missing) >= 3:
        insights.append({
            "type": "diversification",
            "severity": "medium",
            "icon": "🔶",
            "title": "Missing Key Sectors",
            "message": f"Your portfolio lacks exposure to: {', '.join(missing)}.",
            "action": "Broad sector coverage reduces unsystematic risk significantly."
        })

    # ── Beta Alert ────────────────────────────────────────────────
    beta = risk_metrics.get("beta", 1.0)
    if beta > 1.4:
        insights.append({
            "type": "market_risk",
            "severity": "medium",
            "icon": "📡",
            "title": "High Market Sensitivity",
            "message": f"Beta of {beta:.2f} means your portfolio amplifies market moves by {beta:.1f}x.",
            "action": "Add low-beta defensive stocks to reduce market sensitivity."
        })
    elif beta < 0.6:
        insights.append({
            "type": "market_risk",
            "severity": "low",
            "icon": "🛡️",
            "title": "Defensive Portfolio",
            "message": f"Beta of {beta:.2f} means your portfolio is well-insulated from market swings.",
            "action": "Good for capital preservation. If growth is your goal, consider adding some high-beta growth stocks."
        })

    # Sort: high severity first
    severity_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: severity_order.get(x["severity"], 3))

    return insights