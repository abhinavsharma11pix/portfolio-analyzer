import logging
from typing import List
from app.ingestion.schema import UnifiedHolding

logger = logging.getLogger(__name__)


def deduplicate(
    holdings: List[UnifiedHolding]
) -> List[UnifiedHolding]:
    """
    Merge duplicates using weighted average price.
    Keeps highest confidence mapping.
    """
    merged: dict = {}

    for h in holdings:
        key = h.symbol.upper()
        if key not in merged:
            merged[key] = {
                "symbol": h.symbol,
                "exchange": h.exchange,
                "currency": h.currency,
                "sector": h.sector,
                "source": h.source,
                "confidence": h.confidence,
                "raw_symbol": h.raw_symbol,
                "total_qty": h.quantity,
                "total_cost": h.quantity * h.avg_buy_price,
                "warnings": list(h.warnings),
            }
        else:
            ex = merged[key]
            ex["total_qty"] += h.quantity
            ex["total_cost"] += h.quantity * h.avg_buy_price
            # Keep best confidence
            if h.confidence > ex["confidence"]:
                ex["confidence"] = h.confidence
            if not ex["sector"] and h.sector:
                ex["sector"] = h.sector

    result = []
    for data in merged.values():
        qty = data["total_qty"]
        avg = data["total_cost"] / qty if qty > 0 else 0
        result.append(UnifiedHolding(
            symbol=data["symbol"],
            quantity=round(qty, 4),
            avg_buy_price=round(avg, 4),
            exchange=data["exchange"],
            currency=data["currency"],
            sector=data["sector"],
            source=data["source"],
            confidence=data["confidence"],
            raw_symbol=data["raw_symbol"],
            warnings=data["warnings"],
        ))

    dupes = len(holdings) - len(result)
    if dupes > 0:
        logger.info(f"Merged {dupes} duplicate entries")

    return result