from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UnifiedHolding:
    """
    Standard shape for every holding regardless of source.
    confidence: 0.0 - 1.0 (how certain we are about symbol)
    """
    symbol: str
    quantity: float
    avg_buy_price: float
    exchange: str = "NSE"
    currency: str = "INR"
    sector: Optional[str] = None
    source: str = "csv"
    confidence: float = 1.0
    raw_symbol: str = ""        # original symbol before resolution
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_buy_price": self.avg_buy_price,
            "exchange": self.exchange,
            "currency": self.currency,
            "sector": self.sector,
            "source": self.source,
            "confidence": self.confidence,
            "raw_symbol": self.raw_symbol,
            "warnings": self.warnings,
        }


@dataclass
class ValidationResult:
    clean_records: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    low_confidence: list = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def to_dict(self) -> dict:
        return {
            "valid_count": len(self.clean_records),
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "low_confidence_count": len(self.low_confidence),
            "errors": self.errors,
            "warnings": self.warnings,
            "low_confidence": self.low_confidence,
        }