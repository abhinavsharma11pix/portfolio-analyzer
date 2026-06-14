"""
migrations.py — Complete file.
Pure SQLite. Runs on every server start.
Creates all tables if they don't exist yet — safe to run repeatedly.
"""
import logging

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    is_active     INTEGER DEFAULT 1,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT    NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_portfolios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL DEFAULT 'My Portfolio',
    description TEXT,
    is_default  INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
    symbol          TEXT    NOT NULL,
    quantity        REAL    NOT NULL,
    avg_buy_price   REAL    NOT NULL,
    sector          TEXT,
    currency        TEXT    DEFAULT 'INR',
    exchange        TEXT    DEFAULT 'NSE',
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER NOT NULL REFERENCES user_portfolios(id) ON DELETE CASCADE,
    snapshot_date   DATE    NOT NULL,
    total_invested  REAL,
    total_value     REAL,
    total_pnl       REAL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol          TEXT    NOT NULL,
    alert_type      TEXT    NOT NULL,
    threshold       REAL    NOT NULL,
    direction       TEXT    DEFAULT 'both',
    is_active       INTEGER DEFAULT 1,
    notify_email    INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_count INTEGER DEFAULT 0,
    last_triggered  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id      INTEGER REFERENCES alert_rules(id) ON DELETE SET NULL,
    symbol       TEXT    NOT NULL,
    alert_type   TEXT    NOT NULL,
    message      TEXT    NOT NULL,
    value        REAL,
    threshold    REAL,
    severity     TEXT    DEFAULT 'medium',
    is_read      INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id  INTEGER REFERENCES user_portfolios(id) ON DELETE CASCADE,
    symbol        TEXT    NOT NULL,
    trade_type    TEXT    NOT NULL,
    quantity      REAL    NOT NULL,
    price         REAL    NOT NULL,
    total_amount  REAL    NOT NULL,
    trade_date    DATE    NOT NULL,
    exchange      TEXT    DEFAULT 'NSE',
    currency      TEXT    DEFAULT 'INR',
    notes         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ML prediction cache — fixes "no such table: predictions"
CREATE TABLE IF NOT EXISTS predictions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol             TEXT    NOT NULL,
    horizon_days       INTEGER NOT NULL DEFAULT 30,
    current_price      REAL,
    predicted_prices   TEXT,
    confidence_lower   TEXT,
    confidence_upper   TEXT,
    reliability_score  REAL,
    reliability_grade  TEXT,
    models_used        TEXT,
    model_weights      TEXT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_symbol    ON alert_rules(symbol);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user      ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_read    ON alert_history(is_read);
CREATE INDEX IF NOT EXISTS idx_trades_user           ON trades(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_holdings    ON portfolio_holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user   ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_lookup    ON predictions(symbol, horizon_days, created_at);
"""


def run_migrations() -> None:
    """
    Run all migrations. Called once on server startup from main.py lifespan.
    Safe to run multiple times — uses CREATE IF NOT EXISTS everywhere.
    """
    from app.core.database import get_connection

    try:
        conn = get_connection()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        logger.info("✅ DB migrations complete")
    except Exception as e:
        logger.error(f"❌ DB migration failed: {e}")
        raise
