import yfinance as yf
import numpy as np
import pandas as pd
from typing import List, Dict
import time
import logging
logger = logging.getLogger(__name__)


def _download_with_retry(symbol: str, retries: int = 3, delay: float = 2.0) -> pd.DataFrame:
    """Download yfinance data with retry on failure."""
    for attempt in range(retries):
        try:
            data = yf.download(symbol, period="1y", auto_adjust=True, progress=False)
            if not data.empty:
                return data
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {symbol}: {e}")
            time.sleep(delay)
    return pd.DataFrame()


def default_response(error_msg: str = "") -> Dict:
    return {
        "sharpe_ratio": 0,
        "sortino_ratio": 0,
        "annualized_volatility_pct": 0,
        "max_drawdown_pct": 0,
        "beta": 1.0,
        "stock_volatilities": {},
        "interpretation": {
            "sharpe": error_msg or "Insufficient data",
            "volatility": "",
            "drawdown": "",
            "beta": ""
        }
    }


def calculate_risk_metrics(holdings: List[Dict]) -> Dict:
    symbols = [h["symbol"] for h in holdings]
    weights_raw = {h["symbol"]: h["quantity"] * h["avg_buy_price"] for h in holdings}
    total_invested = sum(weights_raw.values())

    if total_invested == 0:
        return default_response("Invalid portfolio weights")

    weights = {s: v / total_invested for s, v in weights_raw.items()}

    # Fetch each stock individually — more reliable than batch
    price_data = {}
    for symbol in symbols:
        try:
            data = _download_with_retry(symbol)
            if not data.empty and "Close" in data.columns:
                close = data["Close"].squeeze()
                if isinstance(close, pd.Series) and len(close) > 50:
                    price_data[symbol] = close
        except Exception:
            continue

    if not price_data:
        return default_response("No valid stock data fetched")

    prices = pd.DataFrame(price_data)
    prices = prices.dropna(axis=1, how="all")

    if prices.empty:
        return default_response("No historical data available")

    returns = prices.pct_change().dropna()

    if returns.empty or len(returns) < 50:
        return default_response("Not enough historical data (need 50+ trading days)")

    available_symbols = [s for s in symbols if s in returns.columns]
    if not available_symbols:
        return default_response("No valid symbols found in historical data")

    available_weights = np.array([weights[s] for s in available_symbols])
    available_weights = available_weights / available_weights.sum()

    portfolio_returns = returns[available_symbols].dot(available_weights)

    # Sharpe Ratio (risk-free = 6.5% India)
    risk_free_daily = 0.065 / 252
    excess_returns = portfolio_returns - risk_free_daily
    sharpe = (
        float((excess_returns.mean() / excess_returns.std()) * np.sqrt(252))
        if excess_returns.std() != 0 else 0.0
    )

    # Annualized Volatility
    volatility = float(portfolio_returns.std() * np.sqrt(252) * 100)

    # Max Drawdown
    cumulative = (1 + portfolio_returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_drawdown = float(drawdown.min() * 100)

    # Beta vs Nifty 50
    try:
        nifty = yf.download("^NSEI", period="1y", auto_adjust=True, progress=False)
        nifty_returns = nifty["Close"].squeeze().pct_change().dropna()
        aligned = pd.concat([portfolio_returns, nifty_returns], axis=1).dropna()
        aligned.columns = ["portfolio", "market"]
        cov = np.cov(aligned["portfolio"], aligned["market"])
        beta = float(cov[0][1] / cov[1][1]) if cov[1][1] != 0 else 1.0
    except Exception:
        beta = 1.0

    # Per-stock volatility
    stock_volatilities = {}
    for symbol in available_symbols:
        vol = float(returns[symbol].std() * np.sqrt(252) * 100)
        stock_volatilities[symbol] = round(vol, 2)

    # Sortino Ratio
    downside = portfolio_returns[portfolio_returns < 0]
    sortino = (
        float((portfolio_returns.mean() * 252) / (downside.std() * np.sqrt(252)))
        if len(downside) > 0 and downside.std() != 0 else 0.0
    )

    return {
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "annualized_volatility_pct": round(volatility, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "beta": round(beta, 3),
        "stock_volatilities": stock_volatilities,
        "interpretation": interpret_metrics(sharpe, volatility, max_drawdown, beta)
    }


def interpret_metrics(sharpe: float, volatility: float, drawdown: float, beta: float) -> Dict:
    return {
        "sharpe": (
            "Excellent risk-adjusted returns" if sharpe > 2 else
            "Good risk-adjusted returns" if sharpe > 1 else
            "Acceptable risk-adjusted returns" if sharpe > 0 else
            "Poor risk-adjusted returns — consider rebalancing"
        ),
        "volatility": (
            "Low volatility — stable portfolio" if volatility < 15 else
            "Moderate volatility — typical for equities" if volatility < 25 else
            "High volatility — significant price swings"
        ),
        "drawdown": (
            "Mild drawdown — resilient portfolio" if drawdown > -15 else
            "Moderate drawdown — acceptable for long-term" if drawdown > -30 else
            "Severe drawdown — portfolio took heavy losses"
        ),
        "beta": (
            "Low market correlation — good diversification" if beta < 0.8 else
            "Moves in line with the market" if beta < 1.2 else
            "High market sensitivity — amplified market moves"
        )
    }