import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# ── Priority levels ──────────────────────────────────────────────
PRIORITY_CRITICAL = 1   # Act today
PRIORITY_HIGH     = 2   # Act this week
PRIORITY_MEDIUM   = 3   # Act this month
PRIORITY_LOW      = 4   # Monitor

PRIORITY_LABELS = {
    1: "🔴 Critical",
    2: "🟠 High",
    3: "🟡 Medium",
    4: "🔵 Low",
}

ACTION_COLORS = {
    "EXIT":      "red",
    "REDUCE":    "orange",
    "TRIM":      "yellow",
    "HOLD":      "gray",
    "ADD":       "green",
    "REBALANCE": "blue",
    "MONITOR":   "gray",
}


@dataclass
class Decision:
    """A single actionable portfolio decision with full explainability."""
    action:           str              # EXIT / REDUCE / TRIM / ADD / REBALANCE
    symbol:           Optional[str]    # Stock symbol if applicable
    priority:         int              # 1=Critical, 2=High, 3=Medium, 4=Low
    title:            str              # Short headline
    what:             str              # Specific action to take
    why:              str              # Reason grounded in data
    metric_triggered: str              # Which metric caused this
    metric_value:     Any              # Current value of that metric
    threshold:        Any              # The threshold that was breached
    impact_score:     float = 0.0     # 0-100 urgency × impact
    confidence:       float = 0.8     # 0-1 confidence in suggestion
    tags:             List[str] = field(default_factory=list)
    suggested_amount: Optional[str] = None  # e.g. "Sell 30% of position"

    def to_dict(self) -> Dict:
        return {
            "action":           self.action,
            "symbol":           self.symbol,
            "priority":         self.priority,
            "priority_label":   PRIORITY_LABELS[self.priority],
            "color":            ACTION_COLORS.get(self.action, "gray"),
            "title":            self.title,
            "what":             self.what,
            "why":              self.why,
            "metric_triggered": self.metric_triggered,
            "metric_value":     self.metric_value,
            "threshold":        self.threshold,
            "impact_score":     round(self.impact_score, 1),
            "confidence":       round(self.confidence, 2),
            "tags":             self.tags,
            "suggested_amount": self.suggested_amount,
        }


def _compute_impact(priority: int, confidence: float) -> float:
    """Impact score = urgency × confidence."""
    urgency_map = {1: 100, 2: 75, 3: 50, 4: 25}
    return urgency_map.get(priority, 25) * confidence


def generate_decisions(
    holdings:        List[Dict],
    risk_metrics:    Dict,
    advanced_metrics: Dict,
    predictions:     Dict,
    summary:         Dict,
) -> List[Decision]:
    """
    Layer 1: Pure rule-based decision generation.
    Zero API calls. Instant. Fully explainable.
    """
    decisions: List[Decision] = []

    total_value = sum(
        h.get("current_value") or h.get("invested_value", 0)
        for h in holdings
    )
    if total_value <= 0:
        return []

    # ── 1. SECTOR CONCENTRATION ───────────────────────────────────
    sector_values: Dict[str, float] = {}
    for h in holdings:
        sector = h.get("sector") or "Unknown"
        val    = h.get("current_value") or h.get("invested_value", 0)
        sector_values[sector] = sector_values.get(sector, 0) + val

    for sector, val in sector_values.items():
        pct = (val / total_value) * 100

        if pct >= 55:
            decisions.append(Decision(
                action="REDUCE",
                symbol=None,
                priority=PRIORITY_CRITICAL,
                title=f"Critical: {sector} concentration at {pct:.1f}%",
                what=f"Reduce {sector} exposure by selling 20-25% of your {sector} holdings",
                why=(
                    f"Your portfolio has {pct:.1f}% in {sector}. "
                    f"A single sector event (earnings miss, regulation, macro) "
                    f"could wipe out more than half your portfolio value. "
                    f"SEBI recommends max 40% in any single sector."
                ),
                metric_triggered="sector_concentration_pct",
                metric_value=round(pct, 1),
                threshold=55,
                confidence=0.95,
                tags=["diversification", "risk", sector.lower()],
                suggested_amount=f"Sell ~{round(val * 0.22):,} worth of {sector} stocks",
            ))
        elif pct >= 40:
            decisions.append(Decision(
                action="MONITOR",
                symbol=None,
                priority=PRIORITY_HIGH,
                title=f"High {sector} exposure: {pct:.1f}%",
                what=f"Plan to reduce {sector} below 35% over the next month",
                why=(
                    f"{sector} makes up {pct:.1f}% of your portfolio. "
                    f"While manageable, any negative sector development "
                    f"would have outsized impact on your returns."
                ),
                metric_triggered="sector_concentration_pct",
                metric_value=round(pct, 1),
                threshold=40,
                confidence=0.80,
                tags=["diversification", sector.lower()],
            ))

    # ── 2. STOP LOSS TRIGGERS ─────────────────────────────────────
    for h in holdings:
        pnl_pct = h.get("pnl_pct")
        if pnl_pct is None:
            continue

        if pnl_pct <= -40:
            decisions.append(Decision(
                action="EXIT",
                symbol=h["symbol"],
                priority=PRIORITY_CRITICAL,
                title=f"Exit {h['symbol']}: down {abs(pnl_pct):.1f}%",
                what=f"Consider exiting your {h['symbol']} position entirely",
                why=(
                    f"{h['symbol']} is down {abs(pnl_pct):.1f}% from your buy price. "
                    f"To recover from this loss, the stock needs to gain "
                    f"{round(100 / (1 - abs(pnl_pct)/100) - 100, 1):.1f}% just to break even. "
                    f"Unless the fundamental thesis has significantly improved, "
                    f"capital is better deployed elsewhere."
                ),
                metric_triggered="pnl_pct",
                metric_value=round(pnl_pct, 1),
                threshold=-40,
                confidence=0.85,
                tags=["stop-loss", "loss", h["symbol"]],
                suggested_amount=f"Exit full position: sell {h['quantity']} shares",
            ))
        elif pnl_pct <= -25:
            decisions.append(Decision(
                action="REDUCE",
                symbol=h["symbol"],
                priority=PRIORITY_HIGH,
                title=f"Reduce {h['symbol']}: down {abs(pnl_pct):.1f}%",
                what=f"Consider reducing {h['symbol']} position by 30-50%",
                why=(
                    f"{h['symbol']} is down {abs(pnl_pct):.1f}%. "
                    f"Reducing position size limits further downside exposure "
                    f"while keeping upside optionality if thesis plays out."
                ),
                metric_triggered="pnl_pct",
                metric_value=round(pnl_pct, 1),
                threshold=-25,
                confidence=0.75,
                tags=["stop-loss", h["symbol"]],
                suggested_amount=f"Sell ~{int(h['quantity'] * 0.4)} shares (40% of position)",
            ))

    # ── 3. PROFIT BOOKING ─────────────────────────────────────────
    for h in holdings:
        pnl_pct = h.get("pnl_pct")
        if pnl_pct is None:
            continue

        if pnl_pct >= 100:
            decisions.append(Decision(
                action="TRIM",
                symbol=h["symbol"],
                priority=PRIORITY_HIGH,
                title=f"Book profits in {h['symbol']}: up {pnl_pct:.1f}%",
                what=f"Sell 30-50% of your {h['symbol']} position to lock in gains",
                why=(
                    f"{h['symbol']} has doubled from your entry price. "
                    f"Booking 30-50% locks in substantial gains while letting "
                    f"the remaining position run. This also reduces position "
                    f"concentration risk."
                ),
                metric_triggered="pnl_pct",
                metric_value=round(pnl_pct, 1),
                threshold=100,
                confidence=0.80,
                tags=["profit-booking", h["symbol"]],
                suggested_amount=f"Sell ~{int(h['quantity'] * 0.35)} shares (35% of position)",
            ))
        elif pnl_pct >= 60:
            decisions.append(Decision(
                action="TRIM",
                symbol=h["symbol"],
                priority=PRIORITY_MEDIUM,
                title=f"Consider trimming {h['symbol']}: up {pnl_pct:.1f}%",
                what=f"Sell 20-25% of {h['symbol']} to lock in partial gains",
                why=(
                    f"{h['symbol']} is up {pnl_pct:.1f}%. "
                    f"Partial profit booking at this level is prudent risk management. "
                    f"It reduces your cost basis and protects against a pullback."
                ),
                metric_triggered="pnl_pct",
                metric_value=round(pnl_pct, 1),
                threshold=60,
                confidence=0.70,
                tags=["profit-booking", h["symbol"]],
                suggested_amount=f"Sell ~{int(h['quantity'] * 0.22)} shares (22% of position)",
            ))

    # ── 4. RISK-ADJUSTED RETURN ───────────────────────────────────
    sharpe = risk_metrics.get("sharpe_ratio", 0)
    vol    = risk_metrics.get("annualized_volatility_pct", 0)

    if sharpe < -0.5:
        decisions.append(Decision(
            action="REBALANCE",
            symbol=None,
            priority=PRIORITY_HIGH,
            title=f"Poor risk-adjusted returns (Sharpe: {sharpe:.2f})",
            what="Shift 20-30% to lower-risk instruments (index funds, liquid funds)",
            why=(
                f"Your Sharpe ratio of {sharpe:.2f} means you are taking on "
                f"significant risk without adequate return compensation. "
                f"A fixed deposit at 7% is currently offering better risk-adjusted "
                f"returns than this portfolio. Defensive repositioning is advised."
            ),
            metric_triggered="sharpe_ratio",
            metric_value=round(sharpe, 2),
            threshold=-0.5,
            confidence=0.90,
            tags=["risk", "rebalance"],
        ))

    if vol > 40:
        decisions.append(Decision(
            action="REBALANCE",
            symbol=None,
            priority=PRIORITY_HIGH,
            title=f"Extreme volatility: {vol:.1f}% annual",
            what="Add 2-3 low-beta defensive stocks (FMCG, Pharma, IT services)",
            why=(
                f"Annual volatility of {vol:.1f}% means your portfolio "
                f"could swing ±{vol/2:.0f}% in either direction this year. "
                f"This level of volatility indicates high portfolio risk. "
                f"Adding defensive holdings reduces overall portfolio beta."
            ),
            metric_triggered="annualized_volatility_pct",
            metric_value=round(vol, 1),
            threshold=40,
            confidence=0.85,
            tags=["volatility", "risk", "rebalance"],
        ))

    # ── 5. DRAWDOWN ALERT ─────────────────────────────────────────
    drawdown = risk_metrics.get("max_drawdown_pct", 0)
    if drawdown < -35:
        decisions.append(Decision(
            action="REBALANCE",
            symbol=None,
            priority=PRIORITY_HIGH,
            title=f"Severe historical drawdown: {drawdown:.1f}%",
            what="Implement position sizing rules and stop-loss discipline",
            why=(
                f"Your portfolio has experienced a {drawdown:.1f}% maximum drawdown. "
                f"This means at some point you were sitting on losses of {abs(drawdown):.0f}% "
                f"from peak. Without stop-loss rules, this pattern will repeat. "
                f"Consider limiting any single position to max 10% of portfolio."
            ),
            metric_triggered="max_drawdown_pct",
            metric_value=round(drawdown, 1),
            threshold=-35,
            confidence=0.80,
            tags=["drawdown", "risk-management"],
        ))

    # ── 6. ADVANCED: VaR BREACH ───────────────────────────────────
    var_95 = advanced_metrics.get("var_95", 0)
    if var_95 < -3.0:
        decisions.append(Decision(
            action="MONITOR",
            symbol=None,
            priority=PRIORITY_MEDIUM,
            title=f"High daily VaR: {var_95:.2f}%",
            what="Monitor portfolio closely — potential for large single-day losses",
            why=(
                f"Your 95% VaR of {var_95:.2f}% means on 1 in 20 trading days "
                f"you could lose more than {abs(var_95):.2f}% of portfolio value. "
                f"This is above typical equity portfolio risk levels."
            ),
            metric_triggered="var_95",
            metric_value=round(var_95, 2),
            threshold=-3.0,
            confidence=0.75,
            tags=["var", "risk"],
        ))

    # ── 7. REGIME-AWARE DECISIONS ─────────────────────────────────
    regime = advanced_metrics.get("regime", {})
    if isinstance(regime, dict):
        if regime.get("regime") == "bear":
            decisions.append(Decision(
                action="REBALANCE",
                symbol=None,
                priority=PRIORITY_HIGH,
                title="Bear market detected — defensive positioning advised",
                what="Increase cash or move 15-20% to gold ETF or short-duration debt",
                why=(
                    f"Regime analysis shows your portfolio is in a bear market phase. "
                    f"30-day trend: {regime.get('trend_pct', 0):.1f}%, "
                    f"volatility: {regime.get('volatility_pct', 0):.1f}%. "
                    f"Historically, capital preservation in bear markets leads to "
                    f"better long-term outcomes than staying fully invested."
                ),
                metric_triggered="market_regime",
                metric_value="bear",
                threshold="bull",
                confidence=0.70,
                tags=["regime", "macro", "defensive"],
            ))

    # ── 8. DIVERSIFICATION GAPS ───────────────────────────────────
    present_sectors = {
        h.get("sector", "Unknown")
        for h in holdings
        if h.get("sector") and h.get("sector") != "Unknown"
    }
    important_sectors = {
        "Healthcare", "FMCG", "Energy",
        "Utilities", "Consumer Staples"
    }
    missing = important_sectors - present_sectors

    if len(missing) >= 3 and len(holdings) >= 5:
        decisions.append(Decision(
            action="ADD",
            symbol=None,
            priority=PRIORITY_MEDIUM,
            title=f"Missing {len(missing)} defensive sectors",
            what=f"Add exposure to: {', '.join(list(missing)[:3])}",
            why=(
                f"Your portfolio has no holdings in {', '.join(missing)}. "
                f"These sectors are typically non-correlated with your "
                f"existing holdings and act as portfolio stabilizers "
                f"during market downturns."
            ),
            metric_triggered="sector_diversity",
            metric_value=len(present_sectors),
            threshold=5,
            confidence=0.70,
            tags=["diversification", "defensive"],
        ))

    # ── 9. PREDICTION-BASED DECISIONS ────────────────────────────
    for symbol, pred in predictions.items():
        if not isinstance(pred, dict):
            continue

        change_30d  = pred.get("predicted_change_pct_30d", 0)
        reliability = pred.get("reliability", {})
        rel_score   = reliability.get("score", 0) if isinstance(reliability, dict) else 0

        # Only act on high-reliability predictions
        if rel_score < 60:
            continue

        if change_30d <= -15:
            # Find the holding
            holding = next((h for h in holdings if h["symbol"] == symbol), None)
            if holding and (holding.get("pnl_pct") or 0) > -10:
                decisions.append(Decision(
                    action="REDUCE",
                    symbol=symbol,
                    priority=PRIORITY_MEDIUM,
                    title=f"ML predicts {symbol} down {abs(change_30d):.1f}% in 30 days",
                    what=f"Consider reducing {symbol} position by 20-30%",
                    why=(
                        f"Our ensemble model (reliability: {rel_score:.0f}/100) "
                        f"predicts {symbol} will decline {abs(change_30d):.1f}% "
                        f"over the next 30 days. While predictions are probabilistic, "
                        f"this level of forecast decline with high model agreement "
                        f"warrants reducing exposure."
                    ),
                    metric_triggered="ml_prediction_30d",
                    metric_value=round(change_30d, 1),
                    threshold=-15,
                    confidence=round(rel_score / 100, 2),
                    tags=["ml-prediction", symbol],
                    suggested_amount=f"Sell ~{int(holding['quantity'] * 0.25)} shares (25% of position)",
                ))

    # ── Compute impact scores and sort ───────────────────────────
    for d in decisions:
        d.impact_score = _compute_impact(d.priority, d.confidence)

    decisions.sort(key=lambda x: (-x.impact_score, x.priority))

    # ── Deduplicate (keep highest priority per symbol) ────────────
    seen_symbols: Dict[str, int] = {}
    deduped = []
    for d in decisions:
        key = d.symbol or d.action
        if key not in seen_symbols:
            seen_symbols[key] = 1
            deduped.append(d)
        elif seen_symbols[key] < 2:
            seen_symbols[key] += 1
            deduped.append(d)

    return deduped