import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from app.core.database import get_connection

logger = logging.getLogger(__name__)


class UserRepository:

    def create(self, email: str, username: str, hashed_password: str) -> Optional[Dict]:
        try:
            conn = get_connection()
            conn.execute(
                "INSERT INTO users (email, username, hashed_password) VALUES (?,?,?)",
                (email.lower().strip(), username.strip(), hashed_password)
            )
            conn.commit()
            user = self.get_by_email(email)
            conn.close()
            return user
        except Exception as e:
            logger.warning(f"Create user failed: {e}")
            return None

    def get_by_email(self, email: str) -> Optional[Dict]:
        conn = get_connection()
        row  = conn.execute(
            "SELECT * FROM users WHERE email=? AND is_active=1",
            (email.lower().strip(),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[Dict]:
        conn = get_connection()
        row  = conn.execute(
            "SELECT * FROM users WHERE id=? AND is_active=1", (user_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def update_last_login(self, user_id: int) -> None:
        conn = get_connection()
        conn.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def email_exists(self, email: str) -> bool:
        conn = get_connection()
        row  = conn.execute("SELECT 1 FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
        conn.close()
        return row is not None

    def username_exists(self, username: str) -> bool:
        conn = get_connection()
        row  = conn.execute("SELECT 1 FROM users WHERE username=?", (username.strip(),)).fetchone()
        conn.close()
        return row is not None


class RefreshTokenRepository:

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def save(self, user_id: int, token: str, expires_at: datetime) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?,?,?)",
            (user_id, self._hash(token), expires_at.isoformat())
        )
        conn.commit()
        conn.close()

    def verify_and_rotate(self, token: str) -> Optional[int]:
        h    = self._hash(token)
        conn = get_connection()
        row  = conn.execute(
            "SELECT id, user_id, expires_at, revoked FROM refresh_tokens WHERE token_hash=?", (h,)
        ).fetchone()
        if not row or row["revoked"]:
            conn.close()
            return None
        if datetime.fromisoformat(row["expires_at"]).replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            conn.close()
            return None
        conn.execute("UPDATE refresh_tokens SET revoked=1 WHERE id=?", (row["id"],))
        conn.commit()
        uid = row["user_id"]
        conn.close()
        return uid

    def revoke_all(self, user_id: int) -> None:
        conn = get_connection()
        conn.execute("UPDATE refresh_tokens SET revoked=1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()


class PortfolioRepository:

    def create(self, user_id: int, name: str, description: str = "") -> Optional[Dict]:
        conn = get_connection()
        cur  = conn.execute(
            "INSERT INTO user_portfolios (user_id, name, description) VALUES (?,?,?)",
            (user_id, name, description)
        )
        conn.commit()
        pid  = cur.lastrowid
        conn.close()
        return self.get_by_id(pid, user_id)

    def get_by_id(self, portfolio_id: int, user_id: int) -> Optional[Dict]:
        conn = get_connection()
        row  = conn.execute(
            """SELECT p.*, COUNT(h.id) as holdings_count
               FROM user_portfolios p
               LEFT JOIN portfolio_holdings h ON h.portfolio_id=p.id
               WHERE p.id=? AND p.user_id=? AND p.is_active=1 GROUP BY p.id""",
            (portfolio_id, user_id)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_for_user(self, user_id: int) -> List[Dict]:
        conn = get_connection()
        rows = conn.execute(
            """SELECT p.*, COUNT(h.id) as holdings_count
               FROM user_portfolios p
               LEFT JOIN portfolio_holdings h ON h.portfolio_id=p.id
               WHERE p.user_id=? AND p.is_active=1
               GROUP BY p.id ORDER BY p.updated_at DESC""",
            (user_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update(self, portfolio_id: int, user_id: int, name: str, description: str = "") -> bool:
        conn = get_connection()
        cur  = conn.execute(
            "UPDATE user_portfolios SET name=?, description=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
            (name, description, portfolio_id, user_id)
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def delete(self, portfolio_id: int, user_id: int) -> bool:
        conn = get_connection()
        cur  = conn.execute(
            "UPDATE user_portfolios SET is_active=0 WHERE id=? AND user_id=?",
            (portfolio_id, user_id)
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def save_holdings(self, portfolio_id: int, holdings: List[Dict]) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM portfolio_holdings WHERE portfolio_id=?", (portfolio_id,))
        for h in holdings:
            conn.execute(
                """INSERT INTO portfolio_holdings
                   (portfolio_id,symbol,exchange,currency,sector,quantity,
                    avg_buy_price,current_price,invested_value,current_value,pnl,pnl_pct)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    portfolio_id,
                    h.get("symbol"), h.get("exchange","NSE"), h.get("currency","INR"),
                    h.get("sector"), h.get("quantity",0), h.get("avg_buy_price",0),
                    h.get("current_price"), h.get("invested_value",0),
                    h.get("current_value"), h.get("pnl"), h.get("pnl_pct"),
                )
            )
        conn.execute(
            "UPDATE user_portfolios SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (portfolio_id,)
        )
        conn.commit()
        conn.close()

    def get_holdings(self, portfolio_id: int, user_id: int) -> List[Dict]:
        conn = get_connection()
        own  = conn.execute(
            "SELECT id FROM user_portfolios WHERE id=? AND user_id=? AND is_active=1",
            (portfolio_id, user_id)
        ).fetchone()
        if not own:
            conn.close()
            return []
        rows = conn.execute(
            "SELECT * FROM portfolio_holdings WHERE portfolio_id=? ORDER BY symbol",
            (portfolio_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_snapshot(self, portfolio_id: int, summary: Dict, risk: Dict = None) -> None:
        today = datetime.now().date().isoformat()
        inr   = summary.get("inr", {})
        conn  = get_connection()
        conn.execute(
            """INSERT INTO portfolio_snapshots
               (portfolio_id,snapshot_date,total_invested,total_value,
                total_pnl,total_pnl_pct,sharpe_ratio,volatility)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(portfolio_id,snapshot_date) DO UPDATE SET
               total_value=excluded.total_value, total_pnl=excluded.total_pnl,
               total_pnl_pct=excluded.total_pnl_pct""",
            (
                portfolio_id, today,
                inr.get("total_invested",0), inr.get("total_current_value",0),
                inr.get("total_pnl",0),      inr.get("total_pnl_pct",0),
                (risk or {}).get("sharpe_ratio",0),
                (risk or {}).get("annualized_volatility_pct",0),
            )
        )
        conn.commit()
        conn.close()

    def get_snapshots(self, portfolio_id: int, user_id: int, days: int = 90) -> List[Dict]:
        conn = get_connection()
        own  = conn.execute(
            "SELECT id FROM user_portfolios WHERE id=? AND user_id=?",
            (portfolio_id, user_id)
        ).fetchone()
        if not own:
            conn.close()
            return []
        rows = conn.execute(
            """SELECT * FROM portfolio_snapshots WHERE portfolio_id=?
               ORDER BY snapshot_date DESC LIMIT ?""",
            (portfolio_id, days)
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]