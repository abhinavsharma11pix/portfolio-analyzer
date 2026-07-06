"""
backend/app/analytics/benchmark.py — Complete rewrite.

Root causes of zeros in the frontend:
  1. Old function returned {"nifty50": {...}, "sp500": {...}} — nested dict.
     Frontend expects flat: {portfolio_return, benchmark_return, alpha, beta,
     correlation, information_ratio, chart_data}. Shape mismatch → all zeros.

  2. Function accepted no benchmark parameter — symbol selected in the UI
     was never used. All buttons (SENSEX, S&P500, NASDAQ) hit the same
     hardcoded loop over all three benchmarks.

  3. Chart data was cumprod * 100 (values ~98–110) instead of cumulative
     % change from 0 (values like -2.1, +7.4). Frontend renders these as
     percentage points so the old values looked insane or invisible.

This version:
  • Accepts a single benchmark_symbol string
  • Returns a flat dict matching BenchmarkChart.tsx exactly
  • Chart data is cumulative % return from 0
  • Adds alpha, correlation, information_ratio, tracking_error
  • Fails gracefully — never raises, returns empty-safe dict on any error
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Supported benchmarks — must match frontend BENCHMARKS array values
BENCHMARK_META: Dict[str, str] = {
    "^NSEI":  "NIFTY 50",
    "^BSESN": "SENSEX",
    "^GSPC":  "S&P 500",
    "^IXIC":  "NASDAQ",
    "^DJI":   "Dow Jones",
}

RISK_FREE_RATE_ANNUAL = 0.065   # ~6.5% Indian 10-yr govt bond proxy


def _empty_result(benchmark_symbol: str) -> Dict:
    """
    Returns a zero-state dict with the correct shape for BenchmarkChart.tsx.
    Used whenever data is unavailable rather than raising an exception.
    """
    return {
        "portfolio_return":  0.0,
        "benchmark_return":  0.0,
        "alpha":             0.0,
        "beta":              1.0,
        "correlation":       0.0,
        "tracking_error":    0.0,
        "information_ratio": 0.0,
        "chart_data":        [],
        "benchmark_name":    BENCHMARK_META.get(benchmark_symbol, benchmark_symbol),
        "data_note":         "Benchmark data temporarily unavailable (yfinance rate limit). Try again in 30s.",
    }


def fetch_benchmark_returns(
    symbol: str,
    period: str = "1y",
) -> Optional[pd.Series]:
    """Fetch daily % returns for a benchmark index. Returns None on failure."""
    try:
        data = yf.download(
            symbol, period=period,
            auto_adjust=True, progress=False,
            timeout=20,
        )
        if data.empty:
            return None

        close = data["Close"].squeeze()
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        returns = close.pct_change().dropna()
        if len(returns) < 20:
            return None

        return returns

    except Exception as e:
        logger.warning(f"Benchmark fetch failed for {symbol}: {e}")
        return None


def compare_portfolio_vs_benchmarks(
    portfolio_returns: pd.Series,
    holdings:          List[Dict],
    benchmark_symbol:  str = "^NSEI",
) -> Dict:
    """
    Compare portfolio vs a single benchmark index.

    Returns flat dict with:
      portfolio_return  — cumulative % return over the period
      benchmark_return  — same for benchmark
      alpha             — portfolio_return - benchmark_return (simple excess return)
      beta              — portfolio beta relative to benchmark
      correlation       — Pearson correlation of daily returns
      tracking_error    — annualised std of (portfolio - benchmark) daily returns
      information_ratio — alpha / tracking_error (annualised)
      chart_data        — [{date, portfolio, benchmark}] cumulative % from 0
      benchmark_name    — human-readable name
    """
    symbol = benchmark_symbol.strip().upper()
    if symbol not in BENCHMARK_META:
        symbol = "^NSEI"

    try:
        bench_returns = fetch_benchmark_returns(symbol)
        if bench_returns is None:
            logger.warning(f"Benchmark {symbol} returned no data")
            return _empty_result(symbol)

        # Align on common trading dates
        aligned = pd.concat(
            [portfolio_returns.rename("portfolio"),
             bench_returns.rename("benchmark")],
            axis=1,
        ).dropna()

        if len(aligned) < 20:
            logger.warning(f"Only {len(aligned)} aligned days for {symbol}")
            return _empty_result(symbol)

        p = aligned["portfolio"]
        b = aligned["benchmark"]

        # ── Cumulative returns ──────────────────────────────────
        port_cum  = float((1 + p).prod() - 1) * 100   # e.g. 12.3 (%)
        bench_cum = float((1 + b).prod() - 1) * 100

        # ── Beta ───────────────────────────────────────────────
        cov_matrix = np.cov(p.values, b.values, ddof=1)
        bench_var  = cov_matrix[1][1]
        beta       = float(cov_matrix[0][1] / bench_var) if bench_var != 0 else 1.0

        # ── Alpha (Jensen's) ───────────────────────────────────
        # Annualised: alpha = port_ann - [rf + beta * (bench_ann - rf)]
        n_years   = len(aligned) / 252
        rf_period = (1 + RISK_FREE_RATE_ANNUAL) ** n_years - 1
        port_total  = (1 + p).prod() - 1
        bench_total = (1 + b).prod() - 1
        alpha_raw = float(port_total - (rf_period + beta * (bench_total - rf_period)))
        alpha_pct = round(alpha_raw * 100, 2)

        # ── Correlation ────────────────────────────────────────
        correlation = float(p.corr(b))
        if np.isnan(correlation):
            correlation = 0.0

        # ── Tracking error and information ratio ───────────────
        active_returns  = p - b
        tracking_error  = float(active_returns.std() * np.sqrt(252) * 100)  # annualised %
        excess_return   = port_cum - bench_cum                               # simple % diff
        information_ratio = (
            round(excess_return / tracking_error, 3)
            if tracking_error > 0 else 0.0
        )

        # ── Chart data — cumulative % return from 0 ────────────
        # Daily resampled to weekly to keep chart readable
        weekly = aligned.resample("W").apply(lambda x: (1 + x).prod() - 1)
        port_cumulative  = ((1 + weekly["portfolio"]).cumprod() - 1) * 100
        bench_cumulative = ((1 + weekly["benchmark"]).cumprod() - 1) * 100

        chart_data = [
            {
                "date":      str(d)[:10],
                "portfolio": round(float(pc), 2),
                "benchmark": round(float(bc), 2),
            }
            for d, pc, bc in zip(
                port_cumulative.index,
                port_cumulative.values,
                bench_cumulative.values,
            )
            if np.isfinite(float(pc)) and np.isfinite(float(bc))
        ]

        return {
            "portfolio_return":  round(port_cum,  2),
            "benchmark_return":  round(bench_cum, 2),
            "alpha":             alpha_pct,
            "beta":              round(beta, 3),
            "correlation":       round(correlation, 3),
            "tracking_error":    round(tracking_error, 2),
            "information_ratio": information_ratio,
            "chart_data":        chart_data,
            "benchmark_name":    BENCHMARK_META.get(symbol, symbol),
            "data_points":       len(aligned),
        }

    except Exception as e:
        logger.exception(f"Benchmark comparison failed for {symbol}: {e}")
        return _empty_result(symbol)
