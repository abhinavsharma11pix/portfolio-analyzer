import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df.get("High", df["Close"])
    low  = df.get("Low",  df["Close"])
    prev = df["Close"].shift(1)
    tr   = pd.concat([
        high - low,
        (high - prev).abs(),
        (low  - prev).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, min_periods=period).mean()


def engineer_features(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Build ML feature matrix from OHLCV data.
    Returns DataFrame with all technical indicators as columns.
    Minimum 60 rows required.
    """
    if df is None or len(df) < 60:
        return None

    f = pd.DataFrame(index=df.index)
    close  = df["Close"].squeeze()
    volume = df.get("Volume", pd.Series(1, index=df.index)).squeeze()

    # ── Trend ────────────────────────────────────────
    f["sma_20"]     = close.rolling(20).mean()
    f["sma_50"]     = close.rolling(50).mean()
    f["ema_12"]     = close.ewm(span=12).mean()
    f["ema_26"]     = close.ewm(span=26).mean()
    f["price_sma20_ratio"] = close / f["sma_20"]
    f["sma20_sma50_ratio"] = f["sma_20"] / f["sma_50"]
    f["trend_signal"]      = (f["sma_20"] > f["sma_50"]).astype(int)

    # ── Momentum ─────────────────────────────────────
    f["rsi_14"]  = compute_rsi(close, 14)
    f["macd"]    = f["ema_12"] - f["ema_26"]
    f["macd_signal"] = f["macd"].ewm(span=9).mean()
    f["macd_hist"]   = f["macd"] - f["macd_signal"]

    # ── Volatility ────────────────────────────────────
    f["bb_mid"]   = close.rolling(20).mean()
    f["bb_std"]   = close.rolling(20).std()
    f["bb_upper"] = f["bb_mid"] + 2 * f["bb_std"]
    f["bb_lower"] = f["bb_mid"] - 2 * f["bb_std"]
    f["bb_width"] = (f["bb_upper"] - f["bb_lower"]) / f["bb_mid"]
    f["bb_pos"]   = (close - f["bb_lower"]) / (
        (f["bb_upper"] - f["bb_lower"]).replace(0, np.nan)
    )
    f["atr_14"]   = compute_atr(df, 14)
    f["volatility_20"] = close.pct_change().rolling(20).std() * np.sqrt(252)

    # ── Volume ────────────────────────────────────────
    f["volume_sma20"] = volume.rolling(20).mean()
    f["volume_ratio"] = volume / f["volume_sma20"].replace(0, np.nan)

    # ── Lag Returns ───────────────────────────────────
    returns = close.pct_change()
    for lag in [1, 3, 5, 10, 21]:
        f[f"return_lag_{lag}"] = returns.shift(lag)

    # ── Target: next-day return ───────────────────────
    f["target"] = returns.shift(-1)
    f["close"]  = close

    f = f.dropna()

    if len(f) < 30:
        return None

    return f