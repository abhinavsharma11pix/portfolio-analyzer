import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Optional
from app.cache import store as cache
from app.cache.symbol_cache import is_delisted, mark_delisted

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


def build_portfolio_returns(
    holdings: List[Dict],
    period:   str = "1y",
) -> Optional[pd.Series]:
    """
    Build weighted daily return series.
    Skips delisted/unavailable symbols gracefully — never returns None
    just because ONE symbol fails.
    """
    if not holdings:
        return None

    # Build weight map — skip zero-value holdings
    weights_raw: Dict[str, float] = {}
    for h in holdings:
        sym = h.get("symbol", "").strip()
        if not sym or is_delisted(sym):
            continue
        inv = float(h.get("invested_value") or 0)
        if inv <= 0:
            inv = float(h.get("quantity") or 0) * float(h.get("avg_buy_price") or 0)
        if inv > 0:
            weights_raw[sym] = inv

    if not weights_raw:
        return None

    total   = sum(weights_raw.values())
    weights = {s: v / total for s, v in weights_raw.items()}
    symbols = list(weights_raw.keys())

    # Cache check
    cache_key = cache.make_portfolio_key(
        "port_ret_v3", [{"s": s} for s in sorted(symbols)], period
    )
    cached = cache.get(cache_key, 1800, disk=True)
    if cached is not None:
        try:
            s = pd.Series(cached)
            if len(s) >= 20:
                return s
        except Exception:
            pass

    # Batch download
    try:
        data = yf.download(
            symbols, period=period,
            auto_adjust=True, progress=False,
            timeout=30, threads=True,
        )
        if data.empty:
            return None

        # Handle both single and multi symbol cases + MultiIndex
        if len(symbols) == 1:
            sym    = symbols[0]
            col    = "Close" if "Close" in data.columns else data.columns[0]
            prices = pd.DataFrame({sym: data[col].squeeze()})
        else:
            if isinstance(data.columns, pd.MultiIndex):
                lvl0 = data.columns.get_level_values(0).unique().tolist()
                lvl1 = data.columns.get_level_values(1).unique().tolist()
                if "Close" in lvl0:
                    prices = data["Close"]
                elif "Close" in lvl1:
                    prices = data.xs("Close", axis=1, level=1)
                else:
                    prices = data.iloc[:, :len(symbols)]
                    prices.columns = symbols[:len(prices.columns)]
            else:
                prices = data["Close"] if "Close" in data.columns else data

        prices  = prices.ffill().dropna(how="all")
        returns = prices.pct_change().dropna()

        if len(returns) < 20:
            return None

        # Only use symbols that actually downloaded
        available = [s for s in symbols if s in returns.columns]
        if not available:
            return None

        # Mark failed symbols as delisted
        failed = [s for s in symbols if s not in returns.columns]
        for sym in failed:
            logger.warning(f"Marking {sym} as delisted — not in download results")
            mark_delisted(sym)

        # Recompute weights for available symbols only
        avail_weights = {s: weights_raw[s] for s in available}
        avail_total   = sum(avail_weights.values())
        w             = np.array([avail_weights[s] / avail_total for s in available])

        port_returns = returns[available].values @ w
        series       = pd.Series(port_returns, index=returns.index).dropna()

        if len(series) >= 20:
            cache.set(cache_key, series.tolist(), 1800, disk=True)
            return series

    except Exception as e:
        logger.warning(f"Portfolio returns build failed: {e}")

    return None