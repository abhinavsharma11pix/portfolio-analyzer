import io
import logging
import pandas as pd
from typing import List, Any
from app.ingestion.base import BaseIngester
from app.ingestion.schema import UnifiedHolding
from app.ingestion.cleaner import clean_dataframe, clean_numeric
from app.ingestion.symbol_resolver import resolve_symbol, detect_exchange, detect_currency

logger = logging.getLogger(__name__)


class ZerodhaIngester(BaseIngester):
    """
    Zerodha Console holdings CSV.
    Download: console.zerodha.com → Holdings → Download
    """
    source_name = "zerodha"

    COLUMN_MAP = {
        "instrument": "symbol",
        "qty.": "quantity",
        "avg._cost": "avg_buy_price",
        "avg_cost": "avg_buy_price",
        "avg._price": "avg_buy_price",
    }

    def ingest(self, raw_data: Any) -> List[UnifiedHolding]:
        contents = (
            raw_data if isinstance(raw_data, bytes)
            else raw_data
        )
        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except Exception:
            df = pd.read_csv(io.StringIO(contents.decode("latin-1")))

        df = clean_dataframe(df)
        df = df.rename(columns=self.COLUMN_MAP)

        if "symbol" not in df.columns:
            logger.error(
                f"Zerodha missing 'Instrument'. "
                f"Found: {list(df.columns)}"
            )
            return []

        holdings = []
        for _, row in df.iterrows():
            try:
                raw_sym = str(row["symbol"]).strip()
                if not raw_sym or raw_sym.lower() == "nan":
                    continue

                # Zerodha uses plain NSE symbols
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
                    source="zerodha",
                    confidence=confidence,
                    raw_symbol=raw_sym,
                ))
            except Exception as e:
                logger.warning(f"Zerodha row skip: {e}")

        logger.info(f"Zerodha: {len(holdings)} holdings parsed")
        return holdings