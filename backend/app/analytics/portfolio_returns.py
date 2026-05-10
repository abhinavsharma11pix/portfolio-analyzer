import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from app.core.analytics_cache import get, set, make_key

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


def build_portfolio_returns(
    holdings: List[Dict],
    period: str = "1y"
) -> Optional[pd.Series]:
    """
    Build weighted daily portfolio return series.
    Cached — avoids repeated yfinance calls.
    """
    symbols = [h["symbol"] for h in holdings]
    cache_key = make_key("port_returns", [{"s": s} for s in symbols], period)
    cached    = get(cache_key, 1800)
    if cached is not None:
        return pd.Series(cached)

    weights_raw = {
        h["symbol"]: h.get("quantity", 0) * h.get("avg_buy_price", 0)
        for h in holdings
    }
    total = sum(weights_raw.values())
    if not total:
        return None

    weights = {s: v / total for s, v in weights_raw.items()}

    try:
        data = yf.download(
            symbols, period=period,
            auto_adjust=True, progress=False,
            timeout=25,
        )
        if data.empty:
            return None

        if len(symbols) == 1:
            prices = data[["Close"]].rename(columns={"Close": symbols[0]})
        else:
            prices = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)

        prices  = prices.dropna(axis=1, how="all")
        returns = prices.pct_change(fill_method=None).dropna()

        available = [s for s in symbols if s in returns.columns]
        if not available:
            return None

        w = np.array([weights[s] for s in available])
        w = w / w.sum()

        port_returns = returns[available].values @ w
        series       = pd.Series(port_returns, index=returns.index)

        # Cache as list for JSON
        set(cache_key, series.tolist())
        return series

    except Exception as e:
        logger.warning(f"Portfolio returns build failed: {e}")
        return None