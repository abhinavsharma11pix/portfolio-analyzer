import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def build_portfolio_returns(
    holdings: List[Dict], period: str = "1y"
) -> Optional[pd.Series]:
    """
    Build weighted daily portfolio return series from holdings.
    """
    symbols = [h["symbol"] for h in holdings]
    weights_raw = {
        h["symbol"]: h["quantity"] * h["avg_buy_price"]
        for h in holdings
    }
    total = sum(weights_raw.values())
    if total == 0:
        return None

    weights = {s: v / total for s, v in weights_raw.items()}

    price_data = {}
    for symbol in symbols:
        try:
            data = yf.download(
                symbol, period=period,
                auto_adjust=True, progress=False
            )
            if not data.empty and "Close" in data.columns:
                close = data["Close"].squeeze()
                if isinstance(close, pd.Series) and len(close) > 20:
                    price_data[symbol] = close
        except Exception:
            continue

    if not price_data:
        return None

    prices = pd.DataFrame(price_data).dropna(axis=1, how="all")
    returns = prices.pct_change(fill_method=None).dropna()

    available = [s for s in symbols if s in returns.columns]
    if not available:
        return None

    w = np.array([weights[s] for s in available])
    w = w / w.sum()

    return returns[available].dot(w)