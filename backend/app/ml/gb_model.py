import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "rsi_14", "macd", "macd_hist", "bb_pos", "bb_width",
    "price_sma20_ratio", "sma20_sma50_ratio", "trend_signal",
    "volume_ratio", "volatility_20",
    "return_lag_1", "return_lag_3", "return_lag_5", "return_lag_10",
]


def fit_gradient_boost(
    features: pd.DataFrame, horizon: int = 30
) -> Optional[Dict]:
    """
    LightGBM-based gradient boosting prediction.
    Falls back to sklearn GBM if LightGBM unavailable.
    """
    try:
        available = [c for c in FEATURE_COLS if c in features.columns]
        if len(available) < 6:
            return None

        X      = features[available].values
        y      = features["target"].values
        prices = features["close"].values

        split   = int(len(X) * 0.8)
        X_train = X[:split]
        y_train = y[:split]

        # Try LightGBM first, fall back to sklearn
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=5,
                num_leaves=31,
                random_state=42,
                verbose=-1,
            )
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor
            model = GradientBoostingRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=4,
                random_state=42,
            )

        model.fit(X_train, y_train)

        current_price = float(prices[-1])
        last_features = X[-1:].copy()

        predictions = []
        upper       = []
        lower       = []
        price       = current_price

        # Historical volatility for CI
        hist_vol = float(pd.Series(y).std())

        for day in range(horizon):
            daily_return = float(model.predict(last_features)[0])
            ci_width     = hist_vol * np.sqrt(day + 1) * 1.96

            price_new = price * (1 + daily_return)
            predictions.append(price_new)
            upper.append(price_new * (1 + ci_width))
            lower.append(price_new * (1 - ci_width))
            price = price_new

        # Clip extremes
        max_val     = current_price * 2.0
        min_val     = current_price * 0.3
        predictions = np.clip(predictions, min_val, max_val).tolist()
        upper       = np.clip(upper, min_val, max_val * 1.2).tolist()
        lower       = np.clip(lower, min_val * 0.8, max_val).tolist()

        return {
            "prices":     predictions,
            "upper":      upper,
            "lower":      lower,
            "price_7d":   predictions[6]  if len(predictions) > 6  else predictions[-1],
            "price_30d":  predictions[-1],
            "model_name": "LightGBM" if "lgb" in str(type(model)) else "GradientBoosting",
        }

    except Exception as e:
        logger.warning(f"Gradient Boost failed: {e}")
        return None