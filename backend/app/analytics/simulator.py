from typing import List, Dict


DEFAULT_SCENARIOS = [
    {
        "name":         "Market Correction (-10%)",
        "market_drop":  0.10,
        "sector_drops": {},
    },
    {
        "name":         "Market Crash (-20%)",
        "market_drop":  0.20,
        "sector_drops": {},
    },
    {
        "name":         "Tech Crash (-40%)",
        "market_drop":  0.05,
        "sector_drops": {"Technology": 0.40},
    },
    {
        "name":         "Banking Crisis (-30%)",
        "market_drop":  0.08,
        "sector_drops": {"Banking": 0.30, "Finance": 0.25},
    },
    {
        "name":         "Energy Shock (-25%)",
        "market_drop":  0.05,
        "sector_drops": {"Energy": 0.25, "Oil & Gas": 0.25},
    },
]


def simulate_scenarios(
    holdings: List[Dict],
    scenarios: List[Dict] = None
) -> List[Dict]:
    """
    Simulate portfolio impact under various crash scenarios.
    Uses beta for market-wide drops, sector drops for targeted crashes.
    """
    if scenarios is None:
        scenarios = DEFAULT_SCENARIOS

    results = []

    total_value = sum(
        h.get("current_value") or h.get("invested_value", 0)
        for h in holdings
    )

    if total_value == 0:
        return results

    for scenario in scenarios:
        market_drop  = scenario.get("market_drop", 0.10)
        sector_drops = scenario.get("sector_drops", {})

        total_loss      = 0.0
        holding_impacts = []

        for h in holdings:
            sector      = h.get("sector") or "Unknown"
            current_val = h.get("current_value") or h.get("invested_value", 0)

            # Use sector-specific drop if defined, else market drop
            if sector in sector_drops:
                drop = sector_drops[sector]
            else:
                drop = market_drop

            loss = current_val * drop
            total_loss += loss

            holding_impacts.append({
                "symbol":               h["symbol"],
                "sector":               sector,
                "current_value":        round(current_val, 2),
                "estimated_loss":       round(loss, 2),
                "estimated_value_after": round(current_val - loss, 2),
                "drop_pct":             round(drop * 100, 1),
            })

        # Sort by loss descending
        holding_impacts.sort(
            key=lambda x: x["estimated_loss"], reverse=True
        )

        results.append({
            "scenario":              scenario["name"],
            "total_portfolio_value": round(total_value, 2),
            "total_loss":            round(total_loss, 2),
            "total_loss_pct":        round((total_loss / total_value) * 100, 2),
            "value_after":           round(total_value - total_loss, 2),
            "holdings":              holding_impacts,
        })

    return results