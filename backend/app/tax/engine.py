"""
India Tax P&L Engine — FY 2024-25 rules.

Key rules (post Budget 2024):
- STCG on listed equity: 20% (held < 12 months)
- LTCG on listed equity: 12.5% (held ≥ 12 months), ₹1.25L exemption
- FIFO matching for multiple lots
- Grandfathering NOT applicable for new purchases after Jan 31 2018
- STT paid assumed (standard listed equity)
"""
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Tax rates FY 2024-25 (Budget 2024 rates)
STCG_RATE          = 0.20    # 20% (changed from 15% from Jul 23 2024)
LTCG_RATE          = 0.125   # 12.5%
LTCG_EXEMPTION     = 125000  # ₹1.25 lakh per year
LTCG_HOLDING_DAYS  = 365     # 12 months for equity

# Surcharge + cess approximation (standard 4% cess)
CESS_RATE          = 0.04


@dataclass
class TradeLot:
    symbol:     str
    buy_date:   date
    quantity:   float
    buy_price:  float
    cost_basis: float   # qty * buy_price


@dataclass
class RealisedGain:
    symbol:       str
    buy_date:     date
    sell_date:    date
    quantity:     float
    buy_price:    float
    sell_price:   float
    cost:         float
    proceeds:     float
    gain:         float
    holding_days: int
    gain_type:    str    # "STCG" or "LTCG"
    tax_rate:     float
    estimated_tax: float


@dataclass
class TaxSummary:
    fy:                   str
    total_stcg:           float
    total_ltcg:           float
    ltcg_exempt:          float
    ltcg_taxable:         float
    stcg_tax:             float
    ltcg_tax:             float
    total_tax:            float
    total_tax_with_cess:  float
    realised_gains:       List[RealisedGain] = field(default_factory=list)
    unrealised_gains:     List[Dict]         = field(default_factory=list)
    harvest_suggestions:  List[Dict]         = field(default_factory=list)


def calculate_tax(
    holdings:    List[Dict],
    trades:      List[Dict] = None,
    target_fy:   str        = None,
) -> Dict:
    """
    Calculate tax liability from holdings + trade history.

    If no trade history provided, treat current holdings as
    unrealised positions and estimate future tax.
    """
    if target_fy is None:
        today   = date.today()
        fy_year = today.year if today.month >= 4 else today.year - 1
        target_fy = f"FY{fy_year}-{str(fy_year+1)[2:]}"

    realised:   List[RealisedGain] = []
    unrealised: List[Dict]         = []

    # ── Process trade history if provided ──────────────────
    if trades:
        realised = _process_trades_fifo(trades, target_fy)

    # ── Process current holdings as unrealised ─────────────
    for h in holdings:
        sym       = h.get("symbol","")
        qty       = float(h.get("quantity") or 0)
        avg_price = float(h.get("avg_buy_price") or 0)
        cur_price = float(h.get("current_price") or avg_price)
        invested  = qty * avg_price
        current   = qty * cur_price
        gain      = current - invested

        if qty <= 0 or avg_price <= 0:
            continue

        # Estimate holding period from avg buy price
        # (without actual buy date, we estimate conservatively)
        unrealised.append({
            "symbol":        sym,
            "quantity":      qty,
            "avg_buy_price": avg_price,
            "current_price": cur_price,
            "invested":      round(invested, 2),
            "current_value": round(current, 2),
            "unrealised_gain": round(gain, 2),
            "unrealised_pct":  round((gain/invested)*100, 2) if invested else 0,
            "estimated_tax_if_sold": _estimate_unrealised_tax(gain),
            "note": "Sell within same year → STCG 20%; hold 12+ months → LTCG 12.5%",
        })

    # ── Compute tax summary ────────────────────────────────
    total_stcg = sum(r.gain for r in realised if r.gain_type == "STCG" and r.gain > 0)
    total_ltcg = sum(r.gain for r in realised if r.gain_type == "LTCG" and r.gain > 0)

    # Also account for loss set-off
    stcg_loss  = sum(r.gain for r in realised if r.gain_type == "STCG" and r.gain < 0)
    ltcg_loss  = sum(r.gain for r in realised if r.gain_type == "LTCG" and r.gain < 0)

    net_stcg   = total_stcg + stcg_loss   # stcg_loss is negative
    net_ltcg   = total_ltcg + ltcg_loss

    # LTCG exemption
    ltcg_exempt  = min(LTCG_EXEMPTION, max(0, net_ltcg))
    ltcg_taxable = max(0, net_ltcg - ltcg_exempt)

    stcg_tax   = max(0, net_stcg)   * STCG_RATE
    ltcg_tax   = ltcg_taxable       * LTCG_RATE
    total_tax  = stcg_tax + ltcg_tax
    with_cess  = total_tax * (1 + CESS_RATE)

    # ── Tax harvesting suggestions ─────────────────────────
    harvest = _generate_harvest_suggestions(unrealised, net_stcg, net_ltcg)

    summary = TaxSummary(
        fy=target_fy,
        total_stcg=round(total_stcg, 2),
        total_ltcg=round(total_ltcg, 2),
        ltcg_exempt=round(ltcg_exempt, 2),
        ltcg_taxable=round(ltcg_taxable, 2),
        stcg_tax=round(stcg_tax, 2),
        ltcg_tax=round(ltcg_tax, 2),
        total_tax=round(total_tax, 2),
        total_tax_with_cess=round(with_cess, 2),
        realised_gains=realised,
        unrealised_gains=unrealised,
        harvest_suggestions=harvest,
    )

    return _serialize(summary)


def _process_trades_fifo(trades: List[Dict], fy: str) -> List[RealisedGain]:
    """FIFO matching of buy → sell trades."""
    # Sort by date
    sorted_trades = sorted(trades, key=lambda t: t.get("trade_date",""))

    # Build lot queues per symbol
    lots: Dict[str, List[TradeLot]] = {}
    realised: List[RealisedGain]    = []

    fy_year    = int(fy[2:6])
    fy_start   = date(fy_year, 4, 1)
    fy_end     = date(fy_year + 1, 3, 31)

    for trade in sorted_trades:
        sym   = trade.get("symbol","")
        ttype = trade.get("trade_type","BUY").upper()
        qty   = float(trade.get("quantity") or 0)
        price = float(trade.get("price") or 0)
        tdate = _parse_date(trade.get("trade_date"))

        if not sym or qty <= 0 or price <= 0 or not tdate:
            continue

        if ttype == "BUY":
            lots.setdefault(sym, []).append(TradeLot(
                symbol=sym, buy_date=tdate, quantity=qty,
                buy_price=price, cost_basis=qty*price
            ))

        elif ttype == "SELL" and sym in lots:
            remaining_sell = qty
            sym_lots       = lots[sym]

            while remaining_sell > 0 and sym_lots:
                lot = sym_lots[0]
                sold_qty = min(remaining_sell, lot.quantity)

                sell_date    = tdate
                holding_days = (sell_date - lot.buy_date).days
                gain_type    = "LTCG" if holding_days >= LTCG_HOLDING_DAYS else "STCG"
                tax_rate     = LTCG_RATE if gain_type == "LTCG" else STCG_RATE
                cost         = sold_qty * lot.buy_price
                proceeds     = sold_qty * price
                gain         = proceeds - cost

                # Only count FY trades
                if fy_start <= sell_date <= fy_end:
                    realised.append(RealisedGain(
                        symbol=sym,
                        buy_date=lot.buy_date,
                        sell_date=sell_date,
                        quantity=sold_qty,
                        buy_price=lot.buy_price,
                        sell_price=price,
                        cost=round(cost,2),
                        proceeds=round(proceeds,2),
                        gain=round(gain,2),
                        holding_days=holding_days,
                        gain_type=gain_type,
                        tax_rate=tax_rate,
                        estimated_tax=round(max(0,gain)*tax_rate, 2),
                    ))

                lot.quantity -= sold_qty
                remaining_sell -= sold_qty
                if lot.quantity <= 0:
                    sym_lots.pop(0)

    return realised


def _estimate_unrealised_tax(gain: float) -> Dict:
    """Estimate tax if sold now (STCG) vs held 12 months (LTCG)."""
    if gain <= 0:
        return {"stcg": 0, "ltcg": 0, "saving": 0}

    stcg_tax  = gain * STCG_RATE
    ltcg_tax  = max(0, gain - LTCG_EXEMPTION) * LTCG_RATE
    saving    = stcg_tax - ltcg_tax

    return {
        "stcg":   round(stcg_tax, 2),
        "ltcg":   round(ltcg_tax, 2),
        "saving": round(saving, 2),
    }


def _generate_harvest_suggestions(
    unrealised: List[Dict],
    net_stcg:   float,
    net_ltcg:   float,
) -> List[Dict]:
    """
    Tax harvesting: suggest selling loss positions to offset gains.
    """
    suggestions = []

    loss_positions = [u for u in unrealised if u["unrealised_gain"] < 0]
    loss_positions.sort(key=lambda x: x["unrealised_gain"])

    if net_stcg > 0 and loss_positions:
        stcg_offset_needed = net_stcg
        for pos in loss_positions:
            loss = abs(pos["unrealised_gain"])
            if stcg_offset_needed <= 0:
                break
            offset = min(loss, stcg_offset_needed)
            tax_saved = offset * STCG_RATE * (1 + CESS_RATE)
            suggestions.append({
                "symbol":       pos["symbol"],
                "action":       "SELL to harvest loss",
                "unrealised_loss": round(-pos["unrealised_gain"], 2),
                "offsets_against": "STCG",
                "tax_saved":     round(tax_saved, 2),
                "explanation":   (
                    f"Selling {pos['symbol']} at current price locks in ₹{abs(pos['unrealised_gain']):,.0f} loss, "
                    f"which offsets your STCG gains. Estimated tax saving: ₹{tax_saved:,.0f}."
                ),
                "buy_back_note": "You can repurchase after 30 days to maintain exposure (wash sale rules don't apply in India).",
            })
            stcg_offset_needed -= offset

    # LTCG utilise exemption
    profit_positions = [u for u in unrealised if u["unrealised_gain"] > 0]
    ltcg_used        = net_ltcg

    if ltcg_used < LTCG_EXEMPTION:
        available = LTCG_EXEMPTION - ltcg_used
        for pos in sorted(profit_positions, key=lambda x: -x["unrealised_gain"])[:3]:
            if pos["unrealised_gain"] <= available:
                suggestions.append({
                    "symbol":        pos["symbol"],
                    "action":        "SELL + REBUY (LTCG exemption harvest)",
                    "unrealised_gain": round(pos["unrealised_gain"], 2),
                    "offsets_against": "LTCG Exemption",
                    "tax_saved":      0,
                    "explanation":    (
                        f"Selling and repurchasing {pos['symbol']} resets your cost basis. "
                        f"₹{pos['unrealised_gain']:,.0f} gain falls within your ₹1.25L LTCG exemption — "
                        f"completely tax-free while stepping up cost basis."
                    ),
                    "buy_back_note": "Repurchase immediately after selling to reset cost basis at no tax cost.",
                })

    return suggestions


def _parse_date(d) -> Optional[date]:
    if not d:
        return None
    if isinstance(d, date):
        return d
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(d), fmt).date()
        except ValueError:
            continue
    return None


def _serialize(summary: TaxSummary) -> Dict:
    return {
        "fy":                   summary.fy,
        "total_stcg":           summary.total_stcg,
        "total_ltcg":           summary.total_ltcg,
        "ltcg_exempt":          summary.ltcg_exempt,
        "ltcg_taxable":         summary.ltcg_taxable,
        "stcg_tax":             summary.stcg_tax,
        "ltcg_tax":             summary.ltcg_tax,
        "total_tax":            summary.total_tax,
        "total_tax_with_cess":  summary.total_tax_with_cess,
        "tax_rates": {
            "stcg":         f"{STCG_RATE*100:.0f}%",
            "ltcg":         f"{LTCG_RATE*100:.1f}%",
            "ltcg_exempt":  f"₹{LTCG_EXEMPTION:,}",
            "cess":         f"{CESS_RATE*100:.0f}%",
            "effective_stcg": f"{STCG_RATE*(1+CESS_RATE)*100:.2f}%",
            "effective_ltcg": f"{LTCG_RATE*(1+CESS_RATE)*100:.3f}%",
        },
        "realised_gains":     [asdict(r) if hasattr(r,'__dataclass_fields__') else r for r in summary.realised_gains],
        "unrealised_gains":   summary.unrealised_gains,
        "harvest_suggestions": summary.harvest_suggestions,
        "summary_text":       _build_summary_text(summary),
    }


def _build_summary_text(s: TaxSummary) -> str:
    if s.total_tax <= 0:
        return (
            f"No realised capital gains for {s.fy}. "
            f"Your unrealised gains are tax-free until you sell."
        )
    return (
        f"For {s.fy}: STCG of ₹{s.total_stcg:,.0f} taxed at 20% = ₹{s.stcg_tax:,.0f}. "
        f"LTCG of ₹{s.total_ltcg:,.0f} with ₹{s.ltcg_exempt:,.0f} exemption, "
        f"taxable = ₹{s.ltcg_taxable:,.0f} at 12.5% = ₹{s.ltcg_tax:,.0f}. "
        f"Total tax (with 4% cess): ₹{s.total_tax_with_cess:,.0f}."
    )