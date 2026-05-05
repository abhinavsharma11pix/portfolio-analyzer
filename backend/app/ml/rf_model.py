import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "rsi_14", "macd", "macd_hist", "bb_pos", "bb_width",
    "price_sma20_ratio", "sma20_sma50_ratio", "trend_signal",
    "volume_ratio", "volatility_20", "atr_14",
    "return_lag_1", "return_lag_3", "return_lag_5",
    "return_lag_10", "return_lag_21",
]


def fit_random_forest(
    features: pd.DataFrame, horizon: int = 30
) -> Optional[Dict]:
    """
    Walk-forward Random Forest prediction.
    Trains on 80% of data, predicts iteratively.
    """
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import RobustScaler

        available = [c for c in FEATURE_COLS if c in features.columns]
        if len(available) < 8:
            return None

        X = features[available].values
        y = features["target"].values
        prices = features["close"].values

        # Train/test split
        split     = int(len(X) * 0.8)
        X_train   = X[:split]
        y_train   = y[:split]

        scaler  = RobustScaler()
        X_train = scaler.fit_transform(X_train)

        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        # Walk-forward prediction
        current_price = float(prices[-1])
        last_features = scaler.transform(X[-1:].reshape(1, -1))

        predictions = []
        upper       = []
        lower       = []
        price       = current_price

        # Get prediction variance from forest
        tree_preds_base = np.array([
            t.predict(last_features)[0]
            for t in model.estimators_
        ])
        pred_std = float(np.std(tree_preds_base))

        for day in range(horizon):
            tree_preds = np.array([
                t.predict(last_features)[0]
                for t in model.estimators_
            ])
            daily_return = float(np.mean(tree_preds))
            ci_width = pred_std * np.sqrt(day + 1) * 1.96

            price_new = price * (1 + daily_return)
            predictions.append(price_new)
            upper.append(price_new * (1 + ci_width))
            lower.append(price_new * (1 - ci_width))
            price = price_new

        # Clip extremes
        max_val = current_price * 2.0
        min_val = current_price * 0.3
        predictions = np.clip(predictions, min_val, max_val).tolist()
        upper       = np.clip(upper, min_val, max_val * 1.2).tolist()
        lower       = np.clip(lower, min_val * 0.8, max_val).tolist()

        return {
            "prices":     predictions,
            "upper":      upper,
            "lower":      lower,
            "price_7d":   predictions[6]  if len(predictions) > 6  else predictions[-1],
            "price_30d":  predictions[-1],
            "model_name": "RandomForest(200)",
            "n_features": len(available),
        }

    except Exception as e:
        logger.warning(f"Random Forest failed: {e}")
        return None