import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_tracked_symbols: list = []


def _refresh_job():
    """Background job: refresh prices for tracked symbols."""
    if not _tracked_symbols:
        return

    from app.data.price_engine import fetch_prices_parallel
    from app.core.market_calendar import get_refresh_interval

    logger.info(
        f"🔄 Auto-refreshing {len(_tracked_symbols)} symbols..."
    )
    try:
        prices = fetch_prices_parallel(_tracked_symbols)
        fetched = sum(1 for v in prices.values() if v)
        logger.info(f"✅ Refreshed {fetched}/{len(_tracked_symbols)} prices")
    except Exception as e:
        logger.error(f"Refresh job failed: {e}")


def start_scheduler(symbols: list = None):
    """Start background price refresh scheduler."""
    global _scheduler, _tracked_symbols

    if symbols:
        _tracked_symbols = symbols

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _refresh_job,
        trigger=IntervalTrigger(minutes=5),
        id="price_refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("✅ Price refresh scheduler started (every 5 min)")


def update_tracked_symbols(symbols: list):
    """Update which symbols are tracked for auto-refresh."""
    global _tracked_symbols
    _tracked_symbols = list(set(symbols))
    logger.info(f"Tracking {len(_tracked_symbols)} symbols for refresh")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")