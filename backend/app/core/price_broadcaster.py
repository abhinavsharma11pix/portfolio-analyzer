import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.core.connection_manager import manager
from app.core.market_calendar import (
    get_refresh_interval, is_nse_open, is_us_open, is_weekend
)
from app.data.price_engine import fetch_prices_parallel

logger = logging.getLogger(__name__)

# Tracked symbols + their baseline prices at session start
_tracked_symbols: List[str] = []
_baseline_prices: Dict[str, float] = {}
_last_prices: Dict[str, float] = {}

ALERT_THRESHOLD_PCT = 2.0  # alert if price moves >2%


def set_tracked_symbols(symbols: List[str]):
    global _tracked_symbols
    _tracked_symbols = list(set(symbols))
    logger.info(f"Now tracking {len(_tracked_symbols)} symbols")


def set_baseline(prices: Dict[str, Optional[float]]):
    """Set baseline prices when portfolio first loaded."""
    global _baseline_prices
    for sym, price in prices.items():
        if price:
            _baseline_prices[sym] = price


def _detect_alerts(
    current: Dict[str, Dict]
) -> List[Dict]:
    """
    Detect significant price movements vs baseline.
    Returns list of alert objects.
    """
    alerts = []
    for symbol, data in current.items():
        price = data.get("price")
        if not price:
            continue

        baseline = _baseline_prices.get(symbol)
        last     = _last_prices.get(symbol)

        # Alert vs baseline (session start)
        if baseline:
            change_pct = ((price - baseline) / baseline) * 100
            if abs(change_pct) >= ALERT_THRESHOLD_PCT:
                alerts.append({
                    "symbol":     symbol,
                    "type":       "session_move",
                    "current":    price,
                    "baseline":   baseline,
                    "change_pct": round(change_pct, 2),
                    "direction":  "up" if change_pct > 0 else "down",
                    "severity":   (
                        "high" if abs(change_pct) >= 5
                        else "medium"
                    ),
                })

        # Alert vs last known (tick move)
        if last and price != last:
            tick_pct = ((price - last) / last) * 100
            if abs(tick_pct) >= 1.0:
                alerts.append({
                    "symbol":     symbol,
                    "type":       "tick_move",
                    "current":    price,
                    "previous":   last,
                    "change_pct": round(tick_pct, 2),
                    "direction":  "up" if tick_pct > 0 else "down",
                    "severity":   "low",
                })

        # Update last known
        if price:
            _last_prices[symbol] = price

    return alerts


async def broadcast_loop():
    """
    Infinite async loop — runs as FastAPI background task.
    Pushes price updates to all WebSocket clients.
    Adapts refresh rate based on connections + market hours.
    """
    logger.info("📡 Price broadcast loop started")

    while True:
        try:
            has_clients = manager.has_active

            # Smart sleep interval
            interval = get_refresh_interval(has_clients)

            if not has_clients:
                # No clients connected — sleep longer
                await asyncio.sleep(min(interval, 60))
                continue

            if not _tracked_symbols:
                await asyncio.sleep(5)
                continue

            # Fetch prices
            price_data = fetch_prices_parallel(
                _tracked_symbols,
                has_active_connections=has_clients
            )

            # Build clean price map
            prices = {
                sym: data["price"]
                for sym, data in price_data.items()
            }

            # Detect alerts
            alerts = _detect_alerts(price_data)

            # Broadcast to all clients
            payload = {
                "type":       "price_update",
                "prices":     prices,
                "alerts":     alerts,
                "market": {
                    "nse_open": is_nse_open(),
                    "us_open":  is_us_open(),
                },
                "sources": {
                    sym: data["source"]
                    for sym, data in price_data.items()
                },
                "stale_symbols": [
                    sym for sym, data in price_data.items()
                    if data.get("stale")
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "next_refresh_seconds": interval,
            }

            await manager.broadcast(payload)

            if alerts:
                logger.info(
                    f"🚨 {len(alerts)} price alerts fired"
                )

        except Exception as e:
            logger.error(f"Broadcast loop error: {e}")

        await asyncio.sleep(interval)