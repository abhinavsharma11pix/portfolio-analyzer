import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from app.cache import store as cache

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


def build_portfolio_returns(
    holdings: List[Dict],
    period: str = "1y",
) -> Optional[pd.Series]:
    """
    Build weighted daily return series.
    Returns None only if truly no data available.
    """
    if not holdings:
        return None

    symbols = [h["symbol"] for h in holdings]
    cache_key = cache.make_portfolio_key("port_ret_v2", [{"s": s} for s in symbols], period)
    cached    = cache.get(cache_key, 1800, disk=True)
    if cached is not None:
        try:
            s = pd.Series(cached)
            if len(s) >= 20:
                return s
        except Exception:
            pass

    # Compute weights from invested value or qty*price
    weights_raw: Dict[str, float] = {}
    for h in holdings:
        inv = float(h.get("invested_value") or 0)
        if inv <= 0:
            qty = float(h.get("quantity") or 0)
            avg = float(h.get("avg_buy_price") or 0)
            inv = qty * avg
        if inv > 0:
            weights_raw[h["symbol"]] = inv

    if not weights_raw:
        return None

    total = sum(weights_raw.values())
    weights = {s: v / total for s, v in weights_raw.items()}

    # Download
    try:
        data = yf.download(
            list(weights_raw.keys()), period=period,
            auto_adjust=True, progress=False,
            timeout=30, threads=True,
        )
        if data.empty:
            return None

        if len(weights_raw) == 1:
            sym    = list(weights_raw.keys())[0]
            prices = pd.DataFrame({sym: data["Close"].squeeze()})
        else:
            if isinstance(data.columns, pd.MultiIndex):
                if "Close" in data.columns.get_level_values(0):
                    prices = data["Close"]
                else:
                    prices = data.xs("Close", axis=1, level=1)
            else:
                prices = data["Close"] if "Close" in data.columns else data

        prices  = prices.ffill().dropna(how="all")
        returns = prices.pct_change().dropna()

        if len(returns) < 20:
            return None

        available = [s for s in weights_raw if s in returns.columns]
        if not available:
            return None

        w = np.array([weights[s] for s in available])
        w = w / w.sum()

        port_returns = returns[available].values @ w
        series       = pd.Series(port_returns, index=returns.index)
        series       = series.dropna()

        if len(series) >= 20:
            cache.set(cache_key, series.tolist(), 1800, disk=True)
            return series

    except Exception as e:
        logger.warning(f"Portfolio returns failed: {e}")

    return None