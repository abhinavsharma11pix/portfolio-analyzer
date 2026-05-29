import logging
from app.core.database import get_connection

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS instrument_master (
    symbol          TEXT PRIMARY KEY,
    exchange        TEXT DEFAULT 'NSE',
    currency        TEXT DEFAULT 'INR',
    sector          TEXT,
    last_price      REAL,
    last_updated    TIMESTAMP,
    is_delisted     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    exchange        TEXT DEFAULT 'NSE',
    currency        TEXT DEFAULT 'INR',
    sector          TEXT,
    quantity        REAL,
    avg_buy_price   REAL,
    current_price   REAL,
    invested_value  REAL,
    current_value   REAL,
    pnl             REAL,
    pnl_pct         REAL,
    confidence      REAL DEFAULT 1.0,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS symbol_aliases (
    raw_input        TEXT PRIMARY KEY,
    resolved_symbol  TEXT NOT NULL,
    confidence       REAL DEFAULT 1.0,
    source           TEXT,
    use_count        INTEGER DEFAULT 1,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    TEXT DEFAULT 'default',
    snapshot_date   DATE NOT NULL,
    total_invested  REAL,
    total_value     REAL,
    total_pnl       REAL,
    total_pnl_pct   REAL,
    sharpe_ratio    REAL,
    volatility      REAL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT UNIQUE NOT NULL COLLATE NOCASE,
    username        TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active       INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_portfolios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT NOT NULL DEFAULT 'My Portfolio',
    description  TEXT DEFAULT '',
    source       TEXT DEFAULT 'manual',
    is_active    INTEGER DEFAULT 1,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    exchange        TEXT DEFAULT 'NSE',
    currency        TEXT DEFAULT 'INR',
    sector          TEXT,
    quantity        REAL NOT NULL DEFAULT 0,
    avg_buy_price   REAL NOT NULL DEFAULT 0,
    current_price   REAL,
    invested_value  REAL DEFAULT 0,
    current_value   REAL,
    pnl             REAL,
    pnl_pct         REAL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, symbol)
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
    snapshot_date   DATE NOT NULL,
    total_invested  REAL DEFAULT 0,
    total_value     REAL DEFAULT 0,
    total_pnl       REAL DEFAULT 0,
    total_pnl_pct   REAL DEFAULT 0,
    holdings_count  INTEGER DEFAULT 0,
    sharpe_ratio    REAL DEFAULT 0,
    volatility      REAL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_users_email         ON users(email);
CREATE INDEX IF NOT EXISTS idx_refresh_user        ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_user      ON user_portfolios(user_id);
CREATE INDEX IF NOT EXISTS idx_ph_portfolio        ON portfolio_holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_ps_portfolio        ON portfolio_snapshots(portfolio_id, snapshot_date);
"""

ALERTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS alert_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    alert_type      TEXT NOT NULL,
    threshold       REAL NOT NULL,
    direction       TEXT DEFAULT 'both',
    is_active       INTEGER DEFAULT 1,
    notify_email    INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_count INTEGER DEFAULT 0,
    last_triggered  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id      INTEGER REFERENCES alert_rules(id) ON DELETE SET NULL,
    symbol       TEXT NOT NULL,
    alert_type   TEXT NOT NULL,
    message      TEXT NOT NULL,
    value        REAL,
    threshold    REAL,
    severity     TEXT DEFAULT 'medium',
    is_read      INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id  INTEGER REFERENCES user_portfolios(id) ON DELETE CASCADE,
    symbol        TEXT NOT NULL,
    trade_type    TEXT NOT NULL CHECK(trade_type IN ('BUY','SELL')),
    quantity      REAL NOT NULL,
    price         REAL NOT NULL,
    total_amount  REAL NOT NULL,
    trade_date    DATE NOT NULL,
    exchange      TEXT DEFAULT 'NSE',
    currency      TEXT DEFAULT 'INR',
    notes         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_symbol ON alert_rules(symbol);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user   ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_read ON alert_history(is_read);
CREATE INDEX IF NOT EXISTS idx_trades_user        ON trades(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_trades_portfolio   ON trades(portfolio_id);
"""


def run_migrations():
    try:
        conn = get_connection()
        conn.executescript(SCHEMA)
        conn.executescript(ALERTS_SCHEMA)
        conn.commit()
        conn.close()
        logger.info("✅ DB migrations complete")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise