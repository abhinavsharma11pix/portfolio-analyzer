import logging
import warnings
import numpy as np
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")


def fit_arima(prices: pd.Series, horizon: int = 30) -> Optional[Dict]:
    """
    Auto-selects best ARIMA order by AIC.
    Returns forecast + confidence intervals.
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller

        if len(prices) < 60:
            return None

        # Stationarity test → determine d
        adf_result = adfuller(prices.dropna())
        d = 0 if adf_result[1] < 0.05 else 1

        # Grid search for best (p, q) by AIC
        best_aic   = np.inf
        best_order = (1, d, 1)

        for p in range(0, 4):
            for q in range(0, 4):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model  = ARIMA(prices, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic   = fitted.aic
                            best_order = (p, d, q)
                except Exception:
                    continue

        # Fit final model
        model  = ARIMA(prices, order=best_order)
        fitted = model.fit()

        forecast_result = fitted.get_forecast(steps=horizon)
        forecast  = forecast_result.predicted_mean
        conf_int  = forecast_result.conf_int(alpha=0.05)

        return {
            "prices":     forecast.tolist(),
            "upper":      conf_int.iloc[:, 1].tolist(),
            "lower":      conf_int.iloc[:, 0].tolist(),
            "price_7d":   float(forecast.iloc[6])  if len(forecast) > 6  else float(forecast.iloc[-1]),
            "price_30d":  float(forecast.iloc[-1]),
            "order":      best_order,
            "aic":        round(best_aic, 2),
            "model_name": f"ARIMA{best_order}",
        }

    except Exception as e:
        logger.warning(f"ARIMA failed: {e}")
        return None