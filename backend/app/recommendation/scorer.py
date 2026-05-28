"""
Real stock scoring engine.
Fixed batch download with proper MultiIndex handling.
Falls back to individual downloads if batch fails.
"""
import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional
from app.cache import store as cache

logger   = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

RF_DAILY   = 0.065 / 252
BATCH_SIZE = 20          # smaller batches = more reliable


def score_stocks_batch(
    symbols_info: List[Dict],
    benchmark:    str = "^NSEI",
    period:       str = "1y",
) -> List[Dict]:
    """
    Score stocks using real yfinance data.
    Uses small batches + individual fallback for reliability.
    """
    if not symbols_info:
        return []

    symbols  = [s["symbol"] for s in symbols_info]
    info_map = {s["symbol"]: s for s in symbols_info}

    # Cache check
    key_symbols = sorted(symbols[:30])  # cache on first 30 for speed
    cache_key   = f"scores_v2:{'|'.join(key_symbols)}:{period}"
    cached      = cache.get(cache_key, 7200, disk=True)
    if cached:
        logger.info(f"Scores from cache: {len(cached)}")
        return cached

    # Download benchmark
    bench_ret = _download_benchmark(benchmark, period)

    all_scored: List[Dict] = []

    # Process in small batches
    for i in range(0, len(symbols), BATCH_SIZE):
        batch  = symbols[i:i + BATCH_SIZE]
        scored = _score_batch(batch, info_map, bench_ret, period)
        all_scored.extend(scored)
        logger.info(f"Scored batch {i//BATCH_SIZE + 1}: {len(scored)}/{len(batch)} stocks")

    # Sort by composite score
    all_scored.sort(key=lambda x: -x.get("composite_score", 0))

    if len(all_scored) >= 3:
        cache.set(cache_key, all_scored, 7200, disk=True)

    logger.info(f"Total scored: {len(all_scored)}/{len(symbols)} stocks")
    return all_scored


def _download_benchmark(benchmark: str, period: str) -> pd.Series:
    key    = f"bench_v2:{benchmark}:{period}"
    cached = cache.get(key, 7200, disk=True)
    if cached:
        return pd.Series(cached)
    try:
        data = yf.download(
            benchmark, period=period,
            auto_adjust=True, progress=False, timeout=15
        )
        if not data.empty:
            prices = data["Close"].squeeze() if "Close" in data.columns else data.iloc[:, 0]
            ret    = prices.pct_change().dropna()
            if len(ret) > 20:
                cache.set(key, ret.tolist(), 7200, disk=True)
                return ret
    except Exception as e:
        logger.debug(f"Benchmark download failed: {e}")
    return pd.Series(dtype=float)


def _score_batch(
    symbols:   List[str],
    info_map:  Dict[str, Dict],
    bench_ret: pd.Series,
    period:    str,
) -> List[Dict]:
    """Download a small batch and score each symbol."""
    if not symbols:
        return []

    prices_map: Dict[str, pd.Series] = {}

    # Try batch download first
    if len(symbols) > 1:
        try:
            raw = yf.download(
                symbols, period=period,
                auto_adjust=True, progress=False,
                timeout=25, threads=True,
            )
            if not raw.empty:
                # Extract close prices robustly
                if isinstance(raw.columns, pd.MultiIndex):
                    lvl0 = raw.columns.get_level_values(0).unique().tolist()
                    lvl1 = raw.columns.get_level_values(1).unique().tolist()
                    if "Close" in lvl0:
                        close_df = raw["Close"]
                    elif "Close" in lvl1:
                        close_df = raw.xs("Close", axis=1, level=1)
                    else:
                        close_df = raw.iloc[:, :len(symbols)]
                        close_df.columns = symbols[:len(close_df.columns)]
                else:
                    close_df = raw["Close"] if "Close" in raw.columns else raw

                close_df = close_df.ffill()
                for sym in symbols:
                    if sym in close_df.columns:
                        s = close_df[sym].dropna()
                        if len(s) >= 50:
                            prices_map[sym] = s
        except Exception as e:
            logger.debug(f"Batch download failed: {e}")

    # Individual fallback for symbols that failed batch
    failed = [s for s in symbols if s not in prices_map]
    if failed:
        for sym in failed:
            try:
                t    = yf.Ticker(sym)
                hist = t.history(period=period, timeout=10)
                if not hist.empty and len(hist) >= 50:
                    prices_map[sym] = hist["Close"]
            except Exception:
                pass

    # Score each available symbol
    scored = []
    for sym, prices in prices_map.items():
        try:
            result = _compute_score(sym, prices, bench_ret, info_map.get(sym, {}))
            scored.append(result)
        except Exception as e:
            logger.debug(f"Score computation failed for {sym}: {e}")

    return scored


def _compute_score(
    symbol:    str,
    prices:    pd.Series,
    bench_ret: pd.Series,
    info:      Dict,
) -> Dict:
    prices  = prices.dropna()
    returns = prices.pct_change().dropna()
    n       = len(returns)

    if n < 30:
        return _default_score(symbol, info)

    # Sharpe
    std    = returns.std()
    sharpe = float((returns.mean() - RF_DAILY) / std * np.sqrt(252)) if std > 0 else 0.0
    sharpe = float(np.clip(sharpe, -3, 5))

    # Sortino
    neg     = returns[returns < 0]
    dstd    = neg.std() if len(neg) > 1 else std
    sortino = float((returns.mean() - RF_DAILY) / dstd * np.sqrt(252)) if dstd > 0 else 0.0

    # Volatility
    vol = float(std * np.sqrt(252) * 100)

    # Momentum
    mom_1y = float((prices.iloc[-1] / prices.iloc[0]  - 1) * 100) if len(prices) > 1   else 0.0
    mid    = max(1, len(prices) // 2)
    mom_6m = float((prices.iloc[-1] / prices.iloc[mid] - 1) * 100) if mid > 0           else 0.0
    mo_1m  = float((prices.iloc[-1] / prices.iloc[max(0, len(prices)-21)] - 1) * 100)

    # Max drawdown
    cum   = (1 + returns).cumprod()
    peak  = cum.cummax()
    denom = peak.replace(0, np.nan)
    max_dd = float(((cum - peak) / denom).min() * 100)

    # Beta
    beta = 1.0
    if len(bench_ret) > 30:
        aligned = pd.concat([returns, bench_ret], axis=1).dropna()
        if len(aligned) > 30:
            cov  = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
            if abs(cov[1][1]) > 1e-10:
                beta = float(np.clip(cov[0][1] / cov[1][1], -2, 4))

    # Trend R²
    x = np.arange(len(prices))
    y = prices.values.astype(float)
    if len(x) > 10 and y.std() > 0:
        p2    = np.polyfit(x, y, 1)
        y_hat = np.polyval(p2, x)
        ss_r  = np.sum((y - y_hat) ** 2)
        ss_t  = np.sum((y - y.mean()) ** 2)
        r2    = 1 - ss_r / ss_t if ss_t > 0 else 0
        trend = float(r2 * np.sign(p2[0]))
    else:
        trend = 0.0

    # Composite 0-100
    sh_n  = _norm(sharpe,  -2,   3)
    so_n  = _norm(sortino, -2,   4)
    mo_n  = _norm(mom_1y,  -40, 80)
    dd_n  = _norm(max_dd,  -60,  0)
    tr_n  = _norm(trend,   -1,   1)

    composite = (sh_n*0.35 + so_n*0.15 + mo_n*0.25 + dd_n*0.15 + tr_n*0.10)
    composite = round(float(np.clip(composite, 0, 100)), 1)

    return {
        "symbol":          symbol,
        "name":            info.get("name", symbol.replace(".NS","").replace(".BO","")),
        "sector":          info.get("sector", "Other"),
        "sharpe":          round(sharpe, 3),
        "sortino":         round(sortino, 3),
        "volatility":      round(vol, 1),
        "momentum_1y":     round(mom_1y, 2),
        "momentum_6m":     round(mom_6m, 2),
        "momentum_1m":     round(mo_1m, 2),
        "max_drawdown":    round(max_dd, 2),
        "beta":            round(beta, 3),
        "trend":           round(trend, 3),
        "composite_score": composite,
        "n_days":          n,
    }


def _norm(val: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 50.0
    return float(np.clip((val - lo) / (hi - lo) * 100, 0, 100))


def _default_score(symbol: str, info: Dict) -> Dict:
    return {
        "symbol": symbol,
        "name":   info.get("name", symbol.replace(".NS","").replace(".BO","")),
        "sector": info.get("sector", "Other"),
        "sharpe": 0.0, "sortino": 0.0, "volatility": 20.0,
        "momentum_1y": 0.0, "momentum_6m": 0.0, "momentum_1m": 0.0,
        "max_drawdown": -15.0, "beta": 1.0, "trend": 0.0,
        "composite_score": 30.0, "n_days": 0,
    }


def select_top_n(
    scored:         List[Dict],
    n:              int,
    max_sector_pct: float = 0.50,
) -> List[Dict]:
    if not scored:
        return []

    selected:      List[Dict]      = []
    sector_counts: Dict[str, int]  = {}
    max_per_sector = max(1, int(n * max_sector_pct))

    for stock in scored:
        if len(selected) >= n:
            break
        sec   = stock.get("sector", "Other")
        count = sector_counts.get(sec, 0)
        if count < max_per_sector:
            selected.append(stock)
            sector_counts[sec] = count + 1

    # Fill remaining if needed
    if len(selected) < n:
        seen = {s["symbol"] for s in selected}
        for stock in scored:
            if len(selected) >= n:
                break
            if stock["symbol"] not in seen:
                selected.append(stock)
                seen.add(stock["symbol"])

    return selected[:n]