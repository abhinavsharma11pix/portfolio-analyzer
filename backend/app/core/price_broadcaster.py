import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.core.connection_manager import manager
from app.core.market_calendar import get_refresh_interval, is_nse_open, is_us_open

logger = logging.getLogger(__name__)

_tracked_symbols: List[str]        = []
_baseline_prices: Dict[str, float] = {}
_last_prices:     Dict[str, float] = {}
_last_broadcast:  float            = 0.0

ALERT_THRESHOLD   = 2.0
MIN_BROADCAST_GAP = 3.0


def set_tracked_symbols(symbols: List[str]) -> None:
    global _tracked_symbols
    _tracked_symbols = list(set(symbols))
    logger.info(f"Tracking {len(_tracked_symbols)} symbols")


def set_baseline(prices: Dict[str, Optional[float]]) -> None:
    global _baseline_prices
    for sym, price in prices.items():
        if price and isinstance(price, (int, float)) and price > 0:
            _baseline_prices[sym] = float(price)


def _detect_alerts(price_data: Dict[str, dict]) -> List[dict]:
    alerts = []
    for symbol, data in price_data.items():
        price = data.get("price")
        if not price:
            continue
        baseline = _baseline_prices.get(symbol)
        if baseline and baseline > 0:
            change_pct = ((price - baseline) / baseline) * 100
            if abs(change_pct) >= ALERT_THRESHOLD:
                alerts.append({
                    "symbol":     symbol,
                    "type":       "session_move",
                    "current":    round(price, 2),
                    "baseline":   round(baseline, 2),
                    "change_pct": round(change_pct, 2),
                    "direction":  "up" if change_pct > 0 else "down",
                    "severity":   "high" if abs(change_pct) >= 5 else "medium",
                })
        _last_prices[symbol] = price
    return alerts


async def broadcast_loop() -> None:
    global _last_broadcast
    logger.info("📡 Broadcast loop started")
    error_count = 0
    interval    = 30

    while True:
        try:
            has_clients = manager.has_active
            interval    = get_refresh_interval(has_clients)

            if not has_clients or not _tracked_symbols:
                await asyncio.sleep(min(interval, 30))
                continue

            now  = time.monotonic()
            wait = max(0, MIN_BROADCAST_GAP - (now - _last_broadcast))
            if wait > 0:
                await asyncio.sleep(wait)

            # ✅ Fixed import path: app.market_data not app.data
            from app.market_data.price_engine import fetch_prices_parallel

            price_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: fetch_prices_parallel(_tracked_symbols, has_clients)
            )

            alerts = _detect_alerts(price_data)
            prices = {s: d.get("price") for s, d in price_data.items()}

            payload = {
                "type":    "price_update",
                "prices":  prices,
                "alerts":  alerts,
                "market": {
                    "nse_open": is_nse_open(),
                    "us_open":  is_us_open(),
                },
                "sources":       {s: d.get("source", "unknown") for s, d in price_data.items()},
                "stale_symbols": [s for s, d in price_data.items() if d.get("stale")],
                "timestamp":     datetime.utcnow().isoformat(),
                "next_refresh_seconds": interval,
            }

            sent = await manager.broadcast(payload)
            _last_broadcast = time.monotonic()

            if alerts:
                logger.info(f"🚨 {len(alerts)} alerts · {sent} clients")

            error_count = 0

        except asyncio.CancelledError:
            logger.info("Broadcast loop cancelled")
            break
        except Exception as e:
            error_count += 1
            wait = min(5 * error_count, 60)
            logger.error(f"Broadcast error (#{error_count}): {e}. Retry in {wait}s")
            await asyncio.sleep(wait)
            continue

        await asyncio.sleep(max(interval - MIN_BROADCAST_GAP, 1))