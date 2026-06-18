"""
migrations.py — Complete file.
Pure SQLite. Runs on every server start.
Safe to run repeatedly — uses CREATE IF NOT EXISTS everywhere.

Fixed vs previous version:
  1. Added `holdings` table          (was missing → background save failed)
  2. Added `instrument_master` table  (was missing → background save failed)
  3. predictions table now has `predicted_at` column
     (code uses predicted_at; previous schema only had created_at → cache never saved
      → every prediction re-ran 3 ML models from scratch → 178s per stock)
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

-- Fix 1: holdings table (used by repositories.py for background upsert after upload)
CREATE TABLE IF NOT EXISTS holdings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT,
    symbol        TEXT    NOT NULL,
    quantity      REAL    NOT NULL,
    avg_buy_price REAL    NOT NULL,
    current_price REAL,
    sector        TEXT,
    currency      TEXT    DEFAULT 'INR',
    exchange      TEXT    DEFAULT 'NSE',
    pnl           REAL,
    pnl_pct       REAL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fix 2: instrument_master table (used by background enrichment after upload)
CREATE TABLE IF NOT EXISTS instrument_master (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT    NOT NULL UNIQUE,
    name          TEXT,
    sector        TEXT,
    industry      TEXT,
    exchange      TEXT,
    currency      TEXT    DEFAULT 'INR',
    market_cap    REAL,
    beta          REAL,
    pe_ratio      REAL,
    country       TEXT,
    last_updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fix 3: predictions table with predicted_at column
-- (code in prediction_service.py uses predicted_at for cache TTL check;
--  previous schema only had created_at → cache write failed → 178s per prediction)
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
    predicted_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alert_rules_symbol     ON alert_rules(symbol);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user       ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_history_read     ON alert_history(is_read);
CREATE INDEX IF NOT EXISTS idx_trades_user            ON trades(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_portfolio_holdings     ON portfolio_holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user    ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_predictions_lookup     ON predictions(symbol, horizon_days, predicted_at);
CREATE INDEX IF NOT EXISTS idx_holdings_session       ON holdings(session_id);
CREATE INDEX IF NOT EXISTS idx_instrument_master_sym  ON instrument_master(symbol);
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