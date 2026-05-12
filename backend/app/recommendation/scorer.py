"""
Real stock scoring engine using yfinance data.
Computes Sharpe, Sortino, Momentum, Drawdown, Beta per stock.
Uses batch download for speed.
Ranks using composite ML-style scoring.
"""
import logging
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional, Tuple
from app.cache import store as cache

logger   = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

RF_DAILY = 0.065 / 252  # 6.5% annual Indian risk-free rate
BATCH_SIZE = 30         # Download 30 symbols at once


def score_stocks_batch(
    symbols_info: List[Dict],
    benchmark:    str = "^NSEI",
    period:       str = "1y",
) -> List[Dict]:
    """
    Score all stocks using real market data.
    Downloads in batches of BATCH_SIZE to avoid rate limits.
    Returns scored list sorted by composite score descending.
    """
    symbols = [s["symbol"] for s in symbols_info]
    info_map = {s["symbol"]: s for s in symbols_info}

    # Cache check per symbol batch
    cache_key = f"scores:{'|'.join(sorted(symbols[:50]))}:{period}"
    cached    = cache.get(cache_key, 7200, disk=True)
    if cached:
        logger.info(f"Scores from cache: {len(cached)} stocks")
        return cached

    # Download benchmark once
    bench_ret = _download_benchmark(benchmark, period)

    all_scored: List[Dict] = []

    # Process in batches
    for i in range(0, len(symbols), BATCH_SIZE):
        batch  = symbols[i:i + BATCH_SIZE]
        scored = _score_batch(batch, info_map, bench_ret, period)
        all_scored.extend(scored)

    # Sort by composite score descending
    all_scored.sort(key=lambda x: -x.get("composite_score", 0))

    if all_scored:
        cache.set(cache_key, all_scored, 7200, disk=True)

    logger.info(f"Scored {len(all_scored)}/{len(symbols)} stocks")
    return all_scored


def _download_benchmark(benchmark: str, period: str) -> pd.Series:
    key    = f"bench:{benchmark}:{period}"
    cached = cache.get(key, 7200, disk=True)
    if cached:
        return pd.Series(cached)
    try:
        data = yf.download(
            benchmark, period=period,
            auto_adjust=True, progress=False, timeout=15
        )
        if not data.empty:
            ret = data["Close"].squeeze().pct_change().dropna()
            cache.set(key, ret.tolist(), 7200, disk=True)
            return ret
    except Exception as e:
        logger.warning(f"Benchmark download failed: {e}")
    return pd.Series(dtype=float)


def _score_batch(
    symbols:    List[str],
    info_map:   Dict[str, Dict],
    bench_ret:  pd.Series,
    period:     str,
) -> List[Dict]:
    """Download and score a batch of symbols."""
    if not symbols:
        return []

    try:
        raw = yf.download(
            symbols, period=period,
            auto_adjust=True, progress=False,
            timeout=20, threads=True,
        )
        if raw.empty:
            return []

        # Extract Close prices
        if isinstance(raw.columns, pd.MultiIndex):
            if "Close" in raw.columns.get_level_values(0):
                prices = raw["Close"]
            elif "Close" in raw.columns.get_level_values(1):
                prices = raw.xs("Close", axis=1, level=1)
            else:
                return []
        else:
            col    = "Close" if "Close" in raw.columns else raw.columns[0]
            prices = raw[[col]].rename(columns={col: symbols[0]})

        prices  = prices.ffill().dropna(how="all")
        returns = prices.pct_change().dropna()

    except Exception as e:
        logger.debug(f"Batch download failed for {symbols[:3]}...: {e}")
        return []

    scored = []
    for sym in symbols:
        if sym not in returns.columns:
            continue

        r = returns[sym].dropna()
        p = prices[sym].dropna()

        if len(r) < 50:  # need at least 50 trading days
            continue

        try:
            scored.append(_compute_score(sym, r, p, bench_ret, info_map.get(sym, {})))
        except Exception:
            continue

    return scored


def _compute_score(
    symbol:    str,
    returns:   pd.Series,
    prices:    pd.Series,
    bench_ret: pd.Series,
    info:      Dict,
) -> Dict:
    """Compute all metrics for a single stock."""
    n = len(returns)

    # ── Sharpe ratio ─────────────────────────────────────────
    std = returns.std()
    sharpe = float((returns.mean() - RF_DAILY) / std * np.sqrt(252)) if std > 0 else 0.0
    sharpe = max(-3.0, min(5.0, sharpe))

    # ── Sortino ratio ─────────────────────────────────────────
    neg    = returns[returns < 0]
    dstd   = neg.std() if len(neg) > 1 else std
    sortino = float((returns.mean() - RF_DAILY) / dstd * np.sqrt(252)) if dstd > 0 else 0.0

    # ── Annualized volatility ─────────────────────────────────
    vol = float(std * np.sqrt(252) * 100)

    # ── Momentum ─────────────────────────────────────────────
    mom_1y = float((prices.iloc[-1] / prices.iloc[0] - 1) * 100) if len(prices) > 1 else 0.0
    mid    = max(1, len(prices) // 2)
    mom_6m = float((prices.iloc[-1] / prices.iloc[mid] - 1) * 100)
    mom_1m = float((prices.iloc[-1] / prices.iloc[max(0, len(prices)-21)] - 1) * 100)

    # ── Max drawdown ─────────────────────────────────────────
    cum     = (1 + returns).cumprod()
    peak    = cum.cummax()
    dd_ser  = (cum - peak) / peak.replace(0, np.nan)
    max_dd  = float(dd_ser.min() * 100) if not dd_ser.empty else 0.0

    # ── Beta vs benchmark ─────────────────────────────────────
    beta = 1.0
    if len(bench_ret) > 30:
        aligned = pd.concat([returns, bench_ret], axis=1).dropna()
        if len(aligned) > 30:
            cov  = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
            if abs(cov[1][1]) > 1e-10:
                beta = float(cov[0][1] / cov[1][1])
                beta = max(-2.0, min(4.0, beta))

    # ── Trend score (R² of price vs time) ────────────────────
    x       = np.arange(len(prices))
    y       = prices.values
    if len(x) > 10:
        p2     = np.polyfit(x, y, 1)
        y_hat  = np.polyval(p2, x)
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2     = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        trend  = float(r2 * np.sign(p2[0]))  # positive if uptrend, negative if down
    else:
        trend = 0.0

    # ── Composite score (0–100) ──────────────────────────────
    # Weights: Sharpe 35%, Sortino 15%, Momentum 25%, Drawdown 15%, Trend 10%
    sh_norm  = _norm(sharpe,   lo=-2, hi=3)   # -2→0, 3→100
    so_norm  = _norm(sortino,  lo=-2, hi=4)
    mo_norm  = _norm(mom_1y,   lo=-40, hi=80) # -40%→0, +80%→100
    dd_norm  = _norm(max_dd,   lo=-60, hi=0)  # -60→0, 0→100 (inverted)
    tr_norm  = _norm(trend,    lo=-1, hi=1)

    composite = (
        sh_norm * 0.35
        + so_norm * 0.15
        + mo_norm * 0.25
        + dd_norm * 0.15
        + tr_norm * 0.10
    )
    composite = round(min(100, max(0, composite)), 1)

    return {
        "symbol":          symbol,
        "name":            info.get("name", symbol),
        "sector":          info.get("sector", "Other"),
        "sharpe":          round(sharpe, 3),
        "sortino":         round(sortino, 3),
        "volatility":      round(vol, 1),
        "momentum_1y":     round(mom_1y, 2),
        "momentum_6m":     round(mom_6m, 2),
        "momentum_1m":     round(mom_1m, 2),
        "max_drawdown":    round(max_dd, 2),
        "beta":            round(beta, 3),
        "trend":           round(trend, 3),
        "composite_score": composite,
        "n_days":          n,
    }


def _norm(val: float, lo: float, hi: float) -> float:
    """Normalize value to 0–100."""
    if hi == lo:
        return 50.0
    return min(100.0, max(0.0, (val - lo) / (hi - lo) * 100))


def select_top_n(
    scored:    List[Dict],
    n:         int,
    max_sector_pct: float = 0.50,
) -> List[Dict]:
    """
    Select top N stocks with sector diversification constraint.
    Ensures no single sector dominates beyond max_sector_pct.
    """
    if not scored:
        return []

    selected:       List[Dict] = []
    sector_counts:  Dict[str, int] = {}
    max_per_sector  = max(1, int(n * max_sector_pct))

    for stock in scored:
        if len(selected) >= n:
            break
        sec   = stock.get("sector", "Other")
        count = sector_counts.get(sec, 0)
        if count < max_per_sector:
            selected.append(stock)
            sector_counts[sec] = count + 1

    # If still short, fill with best remaining regardless of sector
    if len(selected) < n:
        selected_syms = {s["symbol"] for s in selected}
        for stock in scored:
            if len(selected) >= n:
                break
            if stock["symbol"] not in selected_syms:
                selected.append(stock)

    return selected[:n]