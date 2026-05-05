import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Model weights — ARIMA strongest for time-series
WEIGHTS = {"arima": 0.40, "rf": 0.35, "gb": 0.25}


def compute_reliability(
    model_results: Dict[str, Dict],
    data_points: int
) -> Dict:
    """
    Reliability score 0-100 based on:
    1. Model agreement (std dev of 30d predictions)
    2. Data quality (number of points)
    3. Number of models that succeeded
    """
    prices_30d = []
    for name, result in model_results.items():
        if result and result.get("price_30d"):
            prices_30d.append(result["price_30d"])

    n_models = len(prices_30d)

    if n_models == 0:
        return {
            "score": 0,
            "grade": "F",
            "label": "No models succeeded",
            "breakdown": {},
        }

    # Component 1: Model agreement (40 points)
    if n_models >= 2:
        mean_pred    = np.mean(prices_30d)
        std_pred     = np.std(prices_30d)
        disagreement = (std_pred / mean_pred * 100) if mean_pred != 0 else 100
        agreement_score = max(0, 40 - disagreement * 2)
    else:
        agreement_score = 15  # penalty for single model

    # Component 2: Data quality (30 points)
    data_score = min(30, (data_points / 252) * 30)

    # Component 3: Model count (30 points)
    model_score = (n_models / 3) * 30

    total = round(agreement_score + data_score + model_score, 1)
    total = min(100, max(0, total))

    if total >= 80:
        grade, label = "A", "High Confidence"
    elif total >= 65:
        grade, label = "B", "Good Confidence"
    elif total >= 50:
        grade, label = "C", "Moderate Confidence"
    elif total >= 35:
        grade, label = "D", "Low Confidence"
    else:
        grade, label = "F", "Very Low Confidence"

    return {
        "score":       total,
        "grade":       grade,
        "label":       label,
        "n_models":    n_models,
        "disagreement_pct": round(
            (np.std(prices_30d) / np.mean(prices_30d) * 100)
            if len(prices_30d) >= 2 else 0, 2
        ),
        "breakdown": {
            "agreement": round(agreement_score, 1),
            "data_quality": round(data_score, 1),
            "model_coverage": round(model_score, 1),
        }
    }


def build_ensemble(
    model_results: Dict[str, Dict],
    current_price: float,
    horizon: int = 30
) -> Optional[Dict]:
    """
    Weighted ensemble of all successful models.
    Returns unified forecast with empirical confidence intervals.
    """
    successful = {
        k: v for k, v in model_results.items()
        if v and v.get("prices") and len(v["prices"]) >= horizon
    }

    if not successful:
        return None

    # Normalize weights to successful models only
    total_weight = sum(WEIGHTS.get(k, 0.33) for k in successful)
    norm_weights = {
        k: WEIGHTS.get(k, 0.33) / total_weight
        for k in successful
    }

    ensemble_prices = []
    ensemble_upper  = []
    ensemble_lower  = []

    for day in range(horizon):
        day_price  = 0.0
        day_upper  = 0.0
        day_lower  = 0.0

        for model_name, result in successful.items():
            w = norm_weights[model_name]
            day_price += w * result["prices"][day]
            day_upper += w * result["upper"][day]
            day_lower += w * result["lower"][day]

        ensemble_prices.append(round(day_price, 2))
        ensemble_upper.append(round(day_upper, 2))
        ensemble_lower.append(round(day_lower, 2))

    # 7d and 30d predictions
    price_7d  = ensemble_prices[6]  if len(ensemble_prices) > 6  else ensemble_prices[-1]
    price_30d = ensemble_prices[-1]

    change_7d  = round(((price_7d  - current_price) / current_price) * 100, 2) if current_price else 0
    change_30d = round(((price_30d - current_price) / current_price) * 100, 2) if current_price else 0

    # Model breakdown for transparency
    model_breakdown = {}
    for name, result in successful.items():
        p30 = result.get("price_30d", 0)
        chg = round(((p30 - current_price) / current_price) * 100, 2) if current_price else 0
        model_breakdown[name] = {
            "price_30d":   round(p30, 2),
            "change_pct":  chg,
            "model_name":  result.get("model_name", name),
            "weight":      round(norm_weights[name] * 100, 1),
        }

    return {
        "prices":          ensemble_prices,
        "upper":           ensemble_upper,
        "lower":           ensemble_lower,
        "price_7d":        round(price_7d, 2),
        "price_30d":       round(price_30d, 2),
        "change_pct_7d":   change_7d,
        "change_pct_30d":  change_30d,
        "model_breakdown": model_breakdown,
        "models_used":     list(successful.keys()),
    }


def build_future_dates(last_date, horizon: int = 30) -> List[str]:
    """Generate trading-day-aware future dates."""
    dates  = []
    current = pd.Timestamp(last_date)
    while len(dates) < horizon:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            dates.append(str(current.date()))
    return dates