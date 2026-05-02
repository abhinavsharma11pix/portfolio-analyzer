import io
import logging
import pandas as pd
from typing import List, Any
from app.ingestion.base import BaseIngester
from app.ingestion.schema import UnifiedHolding
from app.ingestion.cleaner import clean_dataframe, clean_numeric
from app.ingestion.symbol_resolver import resolve_symbol, detect_exchange, detect_currency

logger = logging.getLogger(__name__)


class GrowwIngester(BaseIngester):
    """
    Groww portfolio export CSV.
    Download: Groww app → Portfolio → Download Statement
    """
    source_name = "groww"

    COLUMN_MAP = {
        "nse_symbol": "symbol",
        "stock_name": "name",
        "average_price": "avg_buy_price",
        "avg_price": "avg_buy_price",
    }

    def ingest(self, raw_data: Any) -> List[UnifiedHolding]:
        contents = (
            raw_data if isinstance(raw_data, bytes)
            else raw_data
        )
        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except Exception as e:
            logger.error(f"Groww parse failed: {e}")
            return []

        df = clean_dataframe(df)
        df = df.rename(columns=self.COLUMN_MAP)

        sym_col = "symbol" if "symbol" in df.columns else "name"
        if sym_col not in df.columns:
            logger.error(f"Groww missing symbol. Found: {list(df.columns)}")
            return []

        holdings = []
        for _, row in df.iterrows():
            try:
                raw_sym = str(row[sym_col]).strip()
                if not raw_sym or raw_sym.lower() == "nan":
                    continue

                symbol, confidence = resolve_symbol(raw_sym)
                if not symbol:
                    continue

                qty   = clean_numeric(row.get("quantity", 0))
                price = clean_numeric(row.get("avg_buy_price", 0))

                if qty <= 0 or price <= 0:
                    continue

                holdings.append(UnifiedHolding(
                    symbol=symbol,
                    quantity=qty,
                    avg_buy_price=price,
                    exchange=detect_exchange(symbol),
                    currency=detect_currency(symbol),
                    source="groww",
                    confidence=confidence,
                    raw_symbol=raw_sym,
                ))
            except Exception as e:
                logger.warning(f"Groww row skip: {e}")

        logger.info(f"Groww: {len(holdings)} holdings parsed")
        return holdings