import logging
import pandas as pd
import io
from app.ingestion.base import BaseIngester
from app.ingestion.csv_ingester import CSVIngester
from app.ingestion.zerodha_ingester import ZerodhaIngester
from app.ingestion.groww_ingester import GrowwIngester
from app.ingestion.pdf_ingester import PDFIngester

logger = logging.getLogger(__name__)


class IngesterFactory:

    @classmethod
    def get(cls, source_type: str) -> BaseIngester:
        mapping = {
            "csv":     CSVIngester,
            "excel":   CSVIngester,
            "xlsx":    CSVIngester,
            "xls":     CSVIngester,
            "zerodha": ZerodhaIngester,
            "groww":   GrowwIngester,
            "pdf":     PDFIngester,
        }
        return mapping.get(source_type.lower(), CSVIngester)()

    @classmethod
    def detect_source(
        cls, filename: str, contents: bytes = None
    ) -> str:
        """
        Smart detection: content-first, filename fallback.
        """
        fname = filename.lower()

        # PDF — always by extension
        if fname.endswith(".pdf"):
            return "pdf"

        # Try content-based detection for CSV/Excel
        if contents:
            source = cls._detect_from_content(
                contents, fname
            )
            if source:
                return source

        # Filename-based fallback
        if "zerodha" in fname:
            return "zerodha"
        if "groww" in fname:
            return "groww"
        if fname.endswith((".xlsx", ".xls")):
            return "excel"

        return "csv"

    @classmethod
    def _detect_from_content(
        cls, contents: bytes, filename: str
    ) -> str | None:
        """
        Detect broker from column headers in file content.
        This is format-independent and future-proof.
        """
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(
                    io.StringIO(contents.decode("utf-8", errors="ignore")),
                    nrows=2
                )
            else:
                df = pd.read_excel(
                    io.BytesIO(contents), nrows=2
                )

            cols = set(
                c.strip().lower()
                for c in df.columns
            )

            # Zerodha signature columns
            if any(c in cols for c in [
                "instrument", "qty.", "avg. cost", "avg_cost"
            ]):
                logger.info("Detected source: zerodha (by content)")
                return "zerodha"

            # Groww signature columns
            if any(c in cols for c in [
                "nse symbol", "stock name", "nse_symbol"
            ]):
                logger.info("Detected source: groww (by content)")
                return "groww"

        except Exception as e:
            logger.debug(f"Content detection failed: {e}")

        return None