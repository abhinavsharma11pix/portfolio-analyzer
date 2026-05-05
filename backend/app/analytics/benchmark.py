import logging
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Dict, List

logger = logging.getLogger(__name__)

BENCHMARKS = {
    "nifty50": {"symbol": "^NSEI",  "name": "Nifty 50",  "currency": "INR"},
    "sp500":   {"symbol": "^GSPC",  "name": "S&P 500",   "currency": "USD"},
    "sensex":  {"symbol": "^BSESN", "name": "Sensex",    "currency": "INR"},
}


def fetch_benchmark_returns(
    symbol: str, period: str = "1y"
) -> pd.Series:
    try:
        data = yf.download(
            symbol, period=period,
            auto_adjust=True, progress=False
        )
        if data.empty:
            return pd.Series(dtype=float)
        return data["Close"].squeeze().pct_change().dropna()
    except Exception as e:
        logger.warning(f"Benchmark fetch failed for {symbol}: {e}")
        return pd.Series(dtype=float)


def compare_portfolio_vs_benchmarks(
    portfolio_returns: pd.Series,
    holdings: List[Dict]
) -> Dict:
    """
    Compare portfolio performance vs Nifty 50 and S&P 500.
    Returns comparison data for charting.
    """
    results = {}

    for key, info in BENCHMARKS.items():
        try:
            bench_returns = fetch_benchmark_returns(info["symbol"])
            if bench_returns.empty:
                continue

            aligned = pd.concat(
                [portfolio_returns, bench_returns], axis=1
            ).dropna()

            if len(aligned) < 20:
                continue

            aligned.columns = ["portfolio", "benchmark"]

            # Cumulative returns
            port_cum  = float((1 + aligned["portfolio"]).prod() - 1) * 100
            bench_cum = float((1 + aligned["benchmark"]).prod() - 1) * 100

            # Annualized returns
            n_years   = len(aligned) / 252
            port_ann  = float((1 + port_cum / 100) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
            bench_ann = float((1 + bench_cum / 100) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0

            # Volatility
            port_vol  = float(aligned["portfolio"].std() * np.sqrt(252) * 100)
            bench_vol = float(aligned["benchmark"].std() * np.sqrt(252) * 100)

            # Beta
            cov  = np.cov(aligned["portfolio"], aligned["benchmark"])
            beta = float(cov[0][1] / cov[1][1]) if cov[1][1] != 0 else 1.0

            # Outperformance
            outperformance = round(port_cum - bench_cum, 2)

            # Build chart data (monthly)
            monthly = aligned.resample("ME").apply(
                lambda x: (1 + x).prod() - 1
            )
            port_growth  = (1 + monthly["portfolio"]).cumprod() * 100
            bench_growth = (1 + monthly["benchmark"]).cumprod() * 100

            chart_data = [
                {
                    "date":      str(d)[:10],
                    "portfolio": round(float(p), 2),
                    "benchmark": round(float(b), 2),
                }
                for d, p, b in zip(
                    port_growth.index,
                    port_growth.values,
                    bench_growth.values
                )
            ]

            results[key] = {
                "name":             info["name"],
                "currency":         info["currency"],
                "portfolio_return": round(port_cum, 2),
                "benchmark_return": round(bench_cum, 2),
                "outperformance":   outperformance,
                "portfolio_vol":    round(port_vol, 2),
                "benchmark_vol":    round(bench_vol, 2),
                "beta":             round(beta, 3),
                "portfolio_ann":    round(port_ann, 2),
                "benchmark_ann":    round(bench_ann, 2),
                "chart_data":       chart_data,
                "beating":          outperformance > 0,
            }

        except Exception as e:
            logger.warning(f"Benchmark comparison failed for {key}: {e}")

    return results