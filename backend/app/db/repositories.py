import logging
from datetime import datetime
from typing import List, Dict, Optional
from app.core.database import get_connection

logger = logging.getLogger(__name__)


class HoldingsRepository:
    """All DB operations for holdings."""

    def upsert(self, holdings: List[Dict],
               portfolio_id: str = "default") -> int:
        """Insert or update holdings. Returns count saved."""
        conn = get_connection()
        saved = 0
        try:
            for h in holdings:
                conn.execute("""
                    INSERT INTO holdings
                        (portfolio_id, symbol, exchange, currency,
                         sector, quantity, avg_buy_price, source, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(portfolio_id, symbol) DO UPDATE SET
                        quantity      = excluded.quantity,
                        avg_buy_price = excluded.avg_buy_price,
                        sector        = excluded.sector,
                        updated_at    = CURRENT_TIMESTAMP
                """, (
                    portfolio_id,
                    h.get("symbol", ""),
                    h.get("exchange", "NSE"),
                    h.get("currency", "INR"),
                    h.get("sector"),
                    h.get("quantity", 0),
                    h.get("avg_buy_price", 0),
                    h.get("source", "csv"),
                ))
                saved += 1
            conn.commit()
            logger.info(f"Saved {saved} holdings to DB")
        except Exception as e:
            conn.rollback()
            logger.error(f"Holdings upsert failed: {e}")
        finally:
            conn.close()
        return saved

    def get_all(self, portfolio_id: str = "default") -> List[Dict]:
        """Fetch all holdings for a portfolio."""
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM holdings
                WHERE portfolio_id = ?
                ORDER BY symbol
            """, (portfolio_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_all(self, portfolio_id: str = "default"):
        """Clear all holdings for a portfolio."""
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM holdings WHERE portfolio_id = ?",
                (portfolio_id,)
            )
            conn.commit()
        finally:
            conn.close()


class PriceCacheRepository:
    """All DB operations for price cache."""

    def set_price(self, symbol: str, price: float,
                  currency: str = "INR",
                  change_pct: float = None,
                  source: str = "yfinance"):
        """Save or update a cached price."""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO price_cache
                    (symbol, price, currency, change_pct,
                     fetched_at, source)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    price      = excluded.price,
                    currency   = excluded.currency,
                    change_pct = excluded.change_pct,
                    fetched_at = CURRENT_TIMESTAMP,
                    source     = excluded.source
            """, (symbol, price, currency, change_pct, source))
            conn.commit()
        finally:
            conn.close()

    def get_price(self, symbol: str,
                  max_age_seconds: int = 300) -> Optional[float]:
        """Get cached price if fresh enough."""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT price FROM price_cache
                WHERE symbol = ?
                AND fetched_at > datetime(
                    'now', ? || ' seconds'
                )
            """, (symbol, f"-{max_age_seconds}")).fetchone()
            return float(row["price"]) if row else None
        finally:
            conn.close()

    def get_all_prices(self) -> Dict[str, float]:
        """Get all cached prices."""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT symbol, price FROM price_cache"
            ).fetchall()
            return {r["symbol"]: float(r["price"]) for r in rows}
        finally:
            conn.close()


class PriceHistoryRepository:
    """Store and retrieve historical OHLCV data."""

    def save_history(self, symbol: str, records: List[Dict]) -> int:
        """Bulk insert historical prices. Skips duplicates."""
        conn = get_connection()
        saved = 0
        try:
            for r in records:
                conn.execute("""
                    INSERT OR IGNORE INTO price_history
                        (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    r.get("date"),
                    r.get("open"),
                    r.get("high"),
                    r.get("low"),
                    r.get("close"),
                    r.get("volume"),
                ))
                saved += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Price history save failed: {e}")
        finally:
            conn.close()
        return saved

    def get_history(self, symbol: str,
                    days: int = 365) -> List[Dict]:
        """Get historical prices for a symbol."""
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT date, close, volume FROM price_history
                WHERE symbol = ?
                AND date >= date('now', ? || ' days')
                ORDER BY date ASC
            """, (symbol, f"-{days}")).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def has_recent_history(self, symbol: str,
                            days_threshold: int = 1) -> bool:
        """Check if we have recent history to avoid re-fetching."""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT MAX(date) as latest FROM price_history
                WHERE symbol = ?
            """, (symbol,)).fetchone()
            if not row or not row["latest"]:
                return False
            from datetime import date, timedelta
            latest = datetime.strptime(
                row["latest"], "%Y-%m-%d"
            ).date()
            threshold = date.today() - timedelta(days=days_threshold)
            return latest >= threshold
        finally:
            conn.close()


class MetricSnapshotRepository:
    """Save computed metrics over time for trend analysis."""

    def save_snapshot(self, metrics: Dict,
                      portfolio_id: str = "default"):
        """Save a metrics snapshot for today."""
        conn = get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO metric_snapshots
                    (portfolio_id, snapshot_date, total_value,
                     total_invested, total_pnl, sharpe_ratio,
                     volatility, max_drawdown, beta, health_score)
                VALUES (?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio_id,
                metrics.get("total_current_value"),
                metrics.get("total_invested"),
                metrics.get("total_pnl"),
                metrics.get("sharpe_ratio"),
                metrics.get("annualized_volatility_pct"),
                metrics.get("max_drawdown_pct"),
                metrics.get("beta"),
                metrics.get("health_score"),
            ))
            conn.commit()
            logger.info("Metric snapshot saved")
        finally:
            conn.close()

    def get_snapshots(self, portfolio_id: str = "default",
                      days: int = 30) -> List[Dict]:
        """Get metric history for trend charts."""
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM metric_snapshots
                WHERE portfolio_id = ?
                AND snapshot_date >= date('now', ? || ' days')
                ORDER BY snapshot_date ASC
            """, (portfolio_id, f"-{days}")).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class PredictionRepository:
    """Cache ML predictions to avoid recomputing."""

    def save_prediction(self, symbol: str, horizon_days: int,
                        predicted_price: float,
                        confidence_high: float,
                        confidence_low: float,
                        model_used: str,
                        reliability_score: float):
        conn = get_connection()
        try:
            conn.execute("""
                INSERT INTO predictions
                    (symbol, predicted_at, horizon_days,
                     predicted_price, confidence_high,
                     confidence_low, model_used, reliability_score)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, horizon_days) DO UPDATE SET
                    predicted_at      = CURRENT_TIMESTAMP,
                    predicted_price   = excluded.predicted_price,
                    confidence_high   = excluded.confidence_high,
                    confidence_low    = excluded.confidence_low,
                    model_used        = excluded.model_used,
                    reliability_score = excluded.reliability_score
            """, (
                symbol, horizon_days, predicted_price,
                confidence_high, confidence_low,
                model_used, reliability_score
            ))
            conn.commit()
        finally:
            conn.close()

    def get_prediction(self, symbol: str,
                       horizon_days: int = 30,
                       max_age_hours: int = 6) -> Optional[Dict]:
        """Get cached prediction if recent enough."""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT * FROM predictions
                WHERE symbol = ?
                AND horizon_days = ?
                AND predicted_at > datetime(
                    'now', ? || ' hours'
                )
            """, (symbol, horizon_days,
                  f"-{max_age_hours}")).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()