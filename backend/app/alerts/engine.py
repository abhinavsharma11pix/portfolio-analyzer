"""
Alert rules engine.
Evaluates price + P&L conditions and fires alerts.
Runs on every WebSocket price broadcast.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from app.core.database import get_connection

logger = logging.getLogger(__name__)

ALERT_TYPES = {
    "price_above":   "Price rose above threshold",
    "price_below":   "Price fell below threshold",
    "price_up_pct":  "Price up % from your buy price",
    "price_down_pct":"Price down % from your buy price",
    "pnl_positive":  "Portfolio in profit",
    "pnl_negative":  "Portfolio loss exceeded threshold",
    "volume_spike":  "Unusual volume detected",
}

SEVERITY_MAP = {
    "price_above":    "low",
    "price_below":    "medium",
    "price_up_pct":   "low",
    "price_down_pct": "high",
    "pnl_positive":   "low",
    "pnl_negative":   "high",
}


class AlertEngine:

    def evaluate_prices(
        self,
        price_data:    Dict[str, Dict],
        holdings:      List[Dict] = None,
    ) -> List[Dict]:
        """
        Evaluate all active alert rules against current prices.
        Returns list of triggered alerts.
        """
        if not price_data:
            return []

        triggered = []
        rules     = self._get_active_rules(list(price_data.keys()))

        for rule in rules:
            sym   = rule["symbol"]
            pdata = price_data.get(sym, {})
            price = pdata.get("price") if isinstance(pdata, dict) else pdata

            if not price:
                continue

            alert = self._evaluate_rule(rule, price, holdings)
            if alert:
                self._save_history(alert)
                self._increment_trigger(rule["id"])
                triggered.append(alert)

        return triggered

    def _evaluate_rule(
        self,
        rule:     Dict,
        price:    float,
        holdings: Optional[List[Dict]],
    ) -> Optional[Dict]:
        atype     = rule["alert_type"]
        threshold = rule["threshold"]
        sym       = rule["symbol"]

        triggered = False
        message   = ""
        value     = price

        if atype == "price_above" and price >= threshold:
            triggered = True
            message   = f"{sym} reached ₹{price:,.2f} (above ₹{threshold:,.2f})"

        elif atype == "price_below" and price <= threshold:
            triggered = True
            message   = f"{sym} dropped to ₹{price:,.2f} (below ₹{threshold:,.2f})"

        elif atype in ("price_up_pct", "price_down_pct") and holdings:
            holding = next((h for h in (holdings or []) if h.get("symbol") == sym), None)
            if holding:
                avg    = float(holding.get("avg_buy_price", 0) or 0)
                if avg > 0:
                    pct    = ((price - avg) / avg) * 100
                    value  = pct
                    if atype == "price_up_pct" and pct >= threshold:
                        triggered = True
                        message   = f"{sym} is up {pct:.1f}% from your buy price of ₹{avg:,.0f}"
                    elif atype == "price_down_pct" and pct <= -abs(threshold):
                        triggered = True
                        message   = f"{sym} is down {abs(pct):.1f}% from your buy price (loss alert)"

        if not triggered:
            return None

        return {
            "rule_id":    rule["id"],
            "symbol":     sym,
            "alert_type": atype,
            "message":    message,
            "value":      round(value, 3),
            "threshold":  threshold,
            "severity":   SEVERITY_MAP.get(atype, "medium"),
            "created_at": datetime.utcnow().isoformat(),
        }

    def _get_active_rules(self, symbols: List[str]) -> List[Dict]:
        if not symbols:
            return []
        conn = get_connection()
        try:
            placeholders = ",".join("?" * len(symbols))
            rows = conn.execute(
                f"SELECT * FROM alert_rules WHERE is_active=1 AND symbol IN ({placeholders})",
                symbols
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.debug(f"Get rules failed: {e}")
            return []
        finally:
            conn.close()

    def _save_history(self, alert: Dict) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO alert_history
                   (rule_id, symbol, alert_type, message, value, threshold, severity)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    alert.get("rule_id"), alert["symbol"], alert["alert_type"],
                    alert["message"], alert.get("value"), alert.get("threshold"),
                    alert.get("severity","medium"),
                )
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"Save alert history failed: {e}")
        finally:
            conn.close()

    def _increment_trigger(self, rule_id: int) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE alert_rules
                   SET triggered_count = triggered_count + 1,
                       last_triggered  = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (rule_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def get_unread_alerts(self, limit: int = 50) -> List[Dict]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM alert_history WHERE is_read=0
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def mark_read(self, alert_ids: List[int]) -> None:
        if not alert_ids:
            return
        conn = get_connection()
        try:
            ph = ",".join("?" * len(alert_ids))
            conn.execute(
                f"UPDATE alert_history SET is_read=1 WHERE id IN ({ph})",
                alert_ids
            )
            conn.commit()
        finally:
            conn.close()

    def mark_all_read(self) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE alert_history SET is_read=1")
            conn.commit()
        finally:
            conn.close()


alert_engine = AlertEngine()