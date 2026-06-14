import logging
import time
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional

from app.ml.feature_engineer import engineer_features
from app.ml.arima_model import fit_arima
from app.ml.rf_model import fit_random_forest
from app.ml.gb_model import fit_gradient_boost
from app.ml.ensemble import (
    build_ensemble, compute_reliability, build_future_dates
)
from app.db.repositories import PredictionRepository

logger = logging.getLogger(__name__)

pred_repo = PredictionRepository()
CACHE_TTL_HOURS = 6


def fetch_ohlcv(symbol: str, period: str = "2y") -> Optional[pd.DataFrame]:
    """Fetch OHLCV with retry. 2 years for better model training."""
    for attempt in range(3):
        try:
            data = yf.download(
                symbol, period=period,
                auto_adjust=True, progress=False
            )
            if not data.empty and len(data) >= 60:
                return data
        except Exception as e:
            if attempt < 2:
                time.sleep(1)
            else:
                logger.warning(f"OHLCV fetch failed for {symbol}: {e}")
    return None


def run_models_parallel(
    features: pd.DataFrame,
    prices: pd.Series,
    horizon: int = 30
) -> Dict:
    """Run all 3 models in parallel for speed."""
    results = {}

    def run_arima():
        return "arima", fit_arima(prices, horizon)

    def run_rf():
        return "rf", fit_random_forest(features, horizon)

    def run_gb():
        return "gb", fit_gradient_boost(features, horizon)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(run_arima),
            executor.submit(run_rf),
            executor.submit(run_gb),
        ]
        for future in as_completed(futures):
            try:
                name, result = future.result(timeout=60)
                results[name] = result
                if result:
                    logger.info(f"✅ {name} succeeded → {result.get('model_name')}")
                else:
                    logger.warning(f"⚠️ {name} returned None")
            except Exception as e:
                logger.warning(f"Model future failed: {e}")

    return results


def generate_prediction(symbol: str, horizon: int = 30) -> Dict:
    """
    Main prediction pipeline.
    Cached → Feature Engineering → 3 Parallel Models → Ensemble → Return
    """
    symbol = symbol.upper().strip()
    start  = time.time()

    # ── 1. Cache check ────────────────────────────────────────────
    try:
        cached = pred_repo.get_prediction(symbol, horizon, CACHE_TTL_HOURS)
    except Exception as e:
        logger.warning(f"Prediction cache read failed (non-fatal): {e}")
        cached = None
    if cached:
        logger.info(f"✅ Cache hit for {symbol}")
        return {**cached, "from_cache": True}

    # ── 2. Fetch data ─────────────────────────────────────────────
    logger.info(f"Fetching OHLCV for {symbol}...")
    ohlcv = fetch_ohlcv(symbol)
    if ohlcv is None:
        return {"error": f"Could not fetch data for {symbol}"}

    prices = ohlcv["Close"].squeeze()
    if not isinstance(prices, pd.Series):
        return {"error": "Invalid price data format"}

    # ── 3. Feature engineering ────────────────────────────────────
    features = engineer_features(ohlcv)
    if features is None:
        return {"error": "Insufficient data for feature engineering (need 60+ days)"}

    data_points   = len(prices)
    current_price = float(prices.iloc[-1])
    last_date     = prices.index[-1]

    logger.info(
        f"Running 3 models in parallel for {symbol} "
        f"({data_points} data points)..."
    )

    # ── 4. Run models in parallel ─────────────────────────────────
    model_results = run_models_parallel(features, prices, horizon)
    models_ran    = sum(1 for v in model_results.values() if v)

    if models_ran == 0:
        return {"error": "All prediction models failed"}

    # ── 5. Ensemble ───────────────────────────────────────────────
    ensemble = build_ensemble(model_results, current_price, horizon)
    if not ensemble:
        return {"error": "Ensemble construction failed"}

    # ── 6. Reliability score ──────────────────────────────────────
    reliability = compute_reliability(model_results, data_points)

    # ── 7. Future dates ───────────────────────────────────────────
    future_dates = build_future_dates(last_date, horizon)

    # ── 8. Historical for chart (last 90 days) ────────────────────
    hist_90 = prices.tail(90)
    historical = [
        {"date": str(d)[:10], "price": round(float(p), 2)}
        for d, p in zip(hist_90.index, hist_90.values)
    ]

    # ── 9. Build forecast chart data ─────────────────────────────
    forecast = [
        {
            "date":      future_dates[i],
            "predicted": ensemble["prices"][i],
            "upper":     ensemble["upper"][i],
            "lower":     ensemble["lower"][i],
        }
        for i in range(min(horizon, len(future_dates)))
    ]

    elapsed = round(time.time() - start, 2)
    logger.info(
        f"✅ {symbol} prediction complete in {elapsed}s | "
        f"Models: {models_ran}/3 | "
        f"Reliability: {reliability['grade']} ({reliability['score']})"
    )

    result = {
        "symbol":           symbol,
        "current_price":    current_price,
        "predicted_price_7d":    ensemble["price_7d"],
        "predicted_price_30d":   ensemble["price_30d"],
        "predicted_change_pct_7d":  ensemble["change_pct_7d"],
        "predicted_change_pct_30d": ensemble["change_pct_30d"],
        "confidence_high":   ensemble["upper"][-1],
        "confidence_low":    ensemble["lower"][-1],
        "reliability":       reliability,
        "model_breakdown":   ensemble["model_breakdown"],
        "models_used":       ensemble["models_used"],
        "historical":        historical,
        "forecast":          forecast,
        "data_points":       data_points,
        "elapsed_seconds":   elapsed,
        "from_cache":        False,
    }

    # ── 10. Cache result ──────────────────────────────────────────
    try:
        pred_repo.save_prediction(
            symbol=symbol,
            horizon_days=horizon,
            predicted_price=ensemble["price_30d"],
            confidence_high=ensemble["upper"][-1],
            confidence_low=ensemble["lower"][-1],
            model_used=",".join(ensemble["models_used"]),
            reliability_score=reliability["score"],
        )
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")

    return result