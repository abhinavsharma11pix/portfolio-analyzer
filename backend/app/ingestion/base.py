from abc import ABC, abstractmethod
from typing import Any, List
from app.ingestion.schema import UnifiedHolding, ValidationResult
from app.ingestion.validator import validate_holdings
from app.ingestion.deduplicator import deduplicate


class BaseIngester(ABC):
    source_name: str = "unknown"

    @abstractmethod
    def ingest(self, raw_data: Any) -> List[UnifiedHolding]:
        raise NotImplementedError

    def process(self, raw_data: Any) -> dict:
        """
        Full pipeline:
        ingest → validate → deduplicate → return
        """
        raw = self.ingest(raw_data)
        validation = validate_holdings(raw)
        clean = deduplicate(validation.clean_records)

        return {
            "holdings": [h.to_dict() for h in clean],
            "validation": validation.to_dict(),
            "total": len(clean),
            "source": self.source_name,
        }