import logging
from typing import List
from app.ingestion.schema import UnifiedHolding, ValidationResult

logger = logging.getLogger(__name__)

MIN_QTY = 0.001
MAX_QTY = 10_000_000
MAX_PRICE = 1_000_000
CONFIDENCE_THRESHOLD = 0.5


def validate_holdings(
    holdings: List[UnifiedHolding]
) -> ValidationResult:
    result = ValidationResult()

    for i, h in enumerate(holdings):
        row_errors = []

        # Symbol
        if not h.symbol:
            row_errors.append(
                f"Row {i+1}: Missing symbol"
            )

        # Quantity
        if h.quantity <= 0:
            row_errors.append(
                f"Row {i+1} ({h.symbol}): "
                f"Invalid quantity {h.quantity}"
            )
        elif h.quantity > MAX_QTY:
            result.warnings.append(
                f"Row {i+1} ({h.symbol}): "
                f"Unusually large quantity {h.quantity}"
            )

        # Price
        if h.avg_buy_price <= 0:
            row_errors.append(
                f"Row {i+1} ({h.symbol}): "
                f"Invalid price {h.avg_buy_price}"
            )
        elif h.avg_buy_price > MAX_PRICE:
            result.warnings.append(
                f"Row {i+1} ({h.symbol}): "
                f"Unusually high price {h.avg_buy_price}"
            )

        # Confidence
        if h.confidence < CONFIDENCE_THRESHOLD:
            result.low_confidence.append({
                "symbol": h.symbol,
                "raw": h.raw_symbol,
                "confidence": h.confidence,
                "suggestion": f"Did you mean {h.symbol}?",
            })

        if row_errors:
            result.errors.extend(row_errors)
        else:
            result.clean_records.append(h)
            result.warnings.extend(h.warnings)

    logger.info(
        f"Validation: {len(result.clean_records)} valid, "
        f"{len(result.errors)} errors, "
        f"{len(result.low_confidence)} low confidence"
    )
    return result