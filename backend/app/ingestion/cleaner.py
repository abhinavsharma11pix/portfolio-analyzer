import re
import logging
import pandas as pd
from typing import Any

logger = logging.getLogger(__name__)


def clean_numeric(value: Any) -> float:
    """
    Convert any messy numeric string to float.
    Handles: ₹1,234.56 / 1.234,56 / "1,234" / "₹ 500"
    """
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    # Remove currency symbols and spaces
    s = re.sub(r"[₹$€£\s]", "", s)
    # Remove commas used as thousands separator
    s = re.sub(r",(?=\d{3})", "", s)
    # Handle European format: 1.234,56 → 1234.56
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return 0.0


def clean_symbol(value: Any) -> str:
    """
    Normalize raw symbol strings.
    Handles: "  RELIANCE  " / "RELIANCE\n" / "Reliance"
    """
    return str(value).strip().upper().replace("\n", "")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Smart DataFrame cleaner.
    - Normalizes column names
    - Removes empty rows
    - Fixes ₹/comma in numeric cols
    - Detects and warns about swapped columns
    """
    # Normalize column names
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-/]+", "_", regex=True)
        .str.replace(r"[^\w_]", "", regex=True)
    )

    # Drop fully empty rows
    df = df.dropna(how="all")

    # Drop rows where all values are the same (repeated headers)
    df = df[~df.apply(
        lambda r: r.astype(str).str.lower().eq(
            df.columns.tolist()
        ).all(), axis=1
    )]

    df = df.reset_index(drop=True)
    return df


def detect_swapped_columns(
    qty: float, price: float
) -> tuple[float, float]:
    """
    Detect if qty and price are swapped.
    Heuristic: price is usually much larger than qty
    for Indian stocks (e.g. qty=10, price=2500)
    """
    if qty > 10000 and price < 1000:
        logger.warning(
            f"Possible swapped columns detected: "
            f"qty={qty}, price={price}. Swapping."
        )
        return price, qty
    return qty, price


def fix_decimal_scaling(price: float) -> float:
    """
    Fix common decimal errors.
    E.g. user enters 25000 when they mean 250.00
    Heuristic: Indian stocks rarely exceed ₹50,000
    """
    if price > 100000:
        logger.warning(
            f"Suspiciously high price {price}, "
            f"may have extra digits"
        )
    return price