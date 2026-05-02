import logging
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from typing import Dict, List

logger = logging.getLogger(__name__)


def fetch_historical(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical OHLCV data for a symbol."""
    try:
        data = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return pd.DataFrame()
        close = data["Close"].squeeze()
        if isinstance(close, pd.Series):
            df = close.reset_index()
            df.columns = ["ds", "y"]
            df = df.dropna()
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()


def predict_trend(df: pd.DataFrame, days: int = 30) -> Dict:
    """
    Ensemble prediction using:
    1. Polynomial regression (captures curves)
    2. Exponential moving average projection
    3. Linear regression baseline
    """
    if df.empty or len(df) < 30:
        return {"error": "Not enough historical data"}

    df = df.copy().reset_index(drop=True)
    df["t"] = np.arange(len(df))
    y = df["y"].values
    t = df["t"].values.reshape(-1, 1)

    # ── Model 1: Polynomial Regression (degree 3) ──────────────
    poly = PolynomialFeatures(degree=3)
    t_poly = poly.fit_transform(t)
    poly_model = LinearRegression()
    poly_model.fit(t_poly, y)

    future_t = np.arange(len(df), len(df) + days).reshape(-1, 1)
    future_t_poly = poly.transform(future_t)
    poly_pred = poly_model.predict(future_t_poly)

    # ── Model 2: EMA Projection ────────────────────────────────
    ema_20 = pd.Series(y).ewm(span=20).mean().values
    ema_slope = (ema_20[-1] - ema_20[-10]) / 10  # slope per day
    ema_pred = np.array([ema_20[-1] + ema_slope * i for i in range(1, days + 1)])

    # ── Model 3: Linear Regression ────────────────────────────
    linear_model = LinearRegression()
    linear_model.fit(t[-60:], y[-60:])  # last 60 days only
    lin_pred = linear_model.predict(future_t)

    # ── Ensemble: weighted average ─────────────────────────────
    # Polynomial gets most weight as it captures trend curves
    ensemble = (0.5 * poly_pred + 0.3 * ema_pred + 0.2 * lin_pred)

    # ── Confidence Interval ────────────────────────────────────
    # Based on historical volatility
    recent_returns = pd.Series(y[-60:]).pct_change().dropna()
    daily_vol = recent_returns.std()
    confidence_factor = daily_vol * np.sqrt(np.arange(1, days + 1))

    upper = ensemble * (1 + 1.96 * confidence_factor)
    lower = ensemble * (1 - 1.96 * confidence_factor)

    # Clip to reasonable bounds (±50% of current price)
    current = float(y[-1])
    max_val = current * 1.5
    min_val = current * 0.5
    ensemble = np.clip(ensemble, min_val, max_val)
    upper = np.clip(upper, min_val, max_val * 1.2)
    lower = np.clip(lower, min_val * 0.8, max_val)

    # ── Build future dates (skip weekends) ────────────────────
    last_date = pd.to_datetime(df["ds"].iloc[-1])
    future_dates = []
    current_date = last_date
    while len(future_dates) < days:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # Mon-Fri only
            future_dates.append(current_date)

    # ── Historical data (last 90 days for chart) ───────────────
    hist_df = df.tail(90).copy()
    historical = [
        {
            "date": str(row["ds"])[:10],
            "price": round(float(row["y"]), 2)
        }
        for _, row in hist_df.iterrows()
    ]

    # ── Forecast data ──────────────────────────────────────────
    forecast = [
        {
            "date": str(future_dates[i])[:10],
            "predicted": round(float(ensemble[i]), 2),
            "upper": round(float(upper[i]), 2),
            "lower": round(float(lower[i]), 2),
        }
        for i in range(days)
    ]

    predicted_price = round(float(ensemble[-1]), 2)
    predicted_change = round(((predicted_price - current) / current) * 100, 2)
    predicted_7d = round(float(ensemble[6]), 2)
    predicted_7d_change = round(((predicted_7d - current) / current) * 100, 2)

    return {
        "symbol": "",
        "current_price": round(current, 2),
        "predicted_price_30d": predicted_price,
        "predicted_change_pct_30d": predicted_change,
        "predicted_price_7d": predicted_7d,
        "predicted_change_pct_7d": predicted_7d_change,
        "confidence_high": round(float(upper[-1]), 2),
        "confidence_low": round(float(lower[-1]), 2),
        "historical": historical,
        "forecast": forecast,
        "model": "Ensemble (Polynomial + EMA + Linear)",
        "data_points": len(df)
    }


def generate_prediction(symbol: str) -> Dict:
    """Main entry point — fetch data and predict."""
    logger.info(f"Generating prediction for {symbol}")

    df = fetch_historical(symbol, period="1y")

    if df.empty:
        return {"error": f"Could not fetch data for {symbol}"}

    result = predict_trend(df, days=30)
    result["symbol"] = symbol
    return result