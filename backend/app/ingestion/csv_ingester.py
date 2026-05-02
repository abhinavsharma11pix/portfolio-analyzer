import io
import logging
import pandas as pd
from typing import List, Any, Optional
from app.ingestion.base import BaseIngester
from app.ingestion.schema import UnifiedHolding
from app.ingestion.cleaner import clean_dataframe, clean_numeric, detect_swapped_columns
from app.ingestion.symbol_resolver import resolve_symbol, detect_exchange, detect_currency

logger = logging.getLogger(__name__)

SYMBOL_COLS = ["symbol", "ticker", "stock", "scrip",
               "instrument", "nse_symbol", "bse_symbol"]
QTY_COLS    = ["quantity", "qty", "shares", "units",
               "no_of_shares", "no__of_shares"]
PRICE_COLS  = ["avg_buy_price", "avg_price", "average_price",
               "buy_price", "cost", "average_cost",
               "purchase_price", "avg__cost"]
SECTOR_COLS = ["sector", "industry", "category"]


def find_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in cols:
            return cols[c]
    return None


class CSVIngester(BaseIngester):
    source_name = "csv"

    def ingest(self, raw_data: Any) -> List[UnifiedHolding]:
        contents = (
            raw_data if isinstance(raw_data, bytes)
            else raw_data
        )
        filename = getattr(raw_data, "filename", "file.csv")
        df = self._parse(contents, filename)
        if df is None or df.empty:
            return []

        df = clean_dataframe(df)

        sym_col    = find_col(df, SYMBOL_COLS)
        qty_col    = find_col(df, QTY_COLS)
        price_col  = find_col(df, PRICE_COLS)
        sector_col = find_col(df, SECTOR_COLS)

        if not sym_col or not qty_col or not price_col:
            logger.error(
                f"Missing required columns. "
                f"Found: {list(df.columns)}"
            )
            return []

        holdings = []
        for _, row in df.iterrows():
            try:
                raw_sym = str(row[sym_col]).strip()
                if not raw_sym or raw_sym.lower() in ("nan", "none", ""):
                    continue

                symbol, confidence = resolve_symbol(raw_sym)
                if not symbol:
                    continue

                qty   = clean_numeric(row[qty_col])
                price = clean_numeric(row[price_col])
                qty, price = detect_swapped_columns(qty, price)

                sector = (
                    str(row[sector_col]).strip()
                    if sector_col and pd.notna(row.get(sector_col))
                    else None
                )

                warnings = []
                if confidence < 0.7:
                    warnings.append(
                        f"'{raw_sym}' resolved to '{symbol}' "
                        f"with {confidence:.0%} confidence"
                    )

                holdings.append(UnifiedHolding(
                    symbol=symbol,
                    quantity=qty,
                    avg_buy_price=price,
                    exchange=detect_exchange(symbol),
                    currency=detect_currency(symbol),
                    sector=sector,
                    source="csv",
                    confidence=confidence,
                    raw_symbol=raw_sym,
                    warnings=warnings,
                ))
            except Exception as e:
                logger.warning(f"Row skip: {e}")

        return holdings

    def _parse(self, contents: bytes, filename: str):
        fname = filename.lower()
        if fname.endswith(".csv"):
            for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                try:
                    return pd.read_csv(
                        io.StringIO(contents.decode(enc))
                    )
                except Exception:
                    continue
        elif fname.endswith((".xlsx", ".xls")):
            try:
                return pd.read_excel(io.BytesIO(contents))
            except Exception as e:
                logger.error(f"Excel parse error: {e}")
        return None