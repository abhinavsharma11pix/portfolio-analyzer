import io
import re
import logging
from typing import List, Any, Optional
from app.ingestion.base import BaseIngester
from app.ingestion.schema import UnifiedHolding
from app.ingestion.cleaner import clean_numeric
from app.ingestion.symbol_resolver import resolve_symbol, detect_exchange, detect_currency

logger = logging.getLogger(__name__)


class PDFIngester(BaseIngester):
    source_name = "pdf"

    def ingest(self, raw_data: Any) -> List[UnifiedHolding]:
        try:
            import pdfplumber
        except ImportError:
            logger.error("Run: pip install pdfplumber")
            return []

        contents = (
            raw_data if isinstance(raw_data, bytes)
            else raw_data
        )
        holdings = []

        try:
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        holdings.extend(self._parse_table(table))
                    if not tables:
                        text = page.extract_text() or ""
                        holdings.extend(self._parse_text(text))
        except Exception as e:
            logger.error(f"PDF error: {e}")

        logger.info(f"PDF: {len(holdings)} holdings extracted")
        return holdings

    def _parse_table(self, table: list) -> List[UnifiedHolding]:
        holdings = []
        if not table or len(table) < 2:
            return holdings

        header = [
            str(c).lower().strip() if c else ""
            for c in table[0]
        ]
        sym_idx   = self._find_col(header, ["symbol", "scrip", "instrument", "stock"])
        qty_idx   = self._find_col(header, ["qty", "quantity", "shares"])
        price_idx = self._find_col(header, ["rate", "price", "avg", "cost"])

        if sym_idx is None:
            return holdings

        for row in table[1:]:
            try:
                if not row or sym_idx >= len(row):
                    continue
                raw_sym = str(row[sym_idx]).strip()
                symbol, confidence = resolve_symbol(raw_sym)
                if not symbol:
                    continue

                qty = clean_numeric(row[qty_idx]) \
                    if qty_idx and qty_idx < len(row) else 0
                price = clean_numeric(row[price_idx]) \
                    if price_idx and price_idx < len(row) else 0

                if qty <= 0:
                    continue

                holdings.append(UnifiedHolding(
                    symbol=symbol,
                    quantity=qty,
                    avg_buy_price=price,
                    exchange=detect_exchange(symbol),
                    currency=detect_currency(symbol),
                    source="pdf",
                    confidence=confidence,
                    raw_symbol=raw_sym,
                ))
            except Exception as e:
                logger.debug(f"PDF row skip: {e}")

        return holdings

    def _parse_text(self, text: str) -> List[UnifiedHolding]:
        holdings = []
        pattern = (
            r"([A-Z]{2,15}(?:\.NS|\.BO)?)"
            r"\s+(\d+(?:\.\d+)?)"
            r"\s+(\d+(?:,\d+)*(?:\.\d+)?)"
        )
        for match in re.findall(pattern, text):
            try:
                raw_sym, qty_str, price_str = match
                symbol, confidence = resolve_symbol(raw_sym)
                if not symbol:
                    continue
                qty   = float(qty_str)
                price = float(price_str.replace(",", ""))
                if qty <= 0 or price <= 0:
                    continue
                holdings.append(UnifiedHolding(
                    symbol=symbol,
                    quantity=qty,
                    avg_buy_price=price,
                    exchange=detect_exchange(symbol),
                    currency=detect_currency(symbol),
                    source="pdf",
                    confidence=confidence,
                    raw_symbol=raw_sym,
                ))
            except ValueError:
                continue
        return holdings

    def _find_col(
        self, header: list, candidates: list
    ) -> Optional[int]:
        for i, h in enumerate(header):
            for c in candidates:
                if c in h:
                    return i
        return None