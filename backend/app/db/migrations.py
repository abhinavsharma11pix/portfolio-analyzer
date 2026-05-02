import logging
from app.core.database import get_connection

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    TEXT NOT NULL DEFAULT 'default',
    symbol          TEXT NOT NULL,
    exchange        TEXT NOT NULL DEFAULT 'NSE',
    currency        TEXT NOT NULL DEFAULT 'INR',
    sector          TEXT,
    quantity        REAL NOT NULL,
    avg_buy_price   REAL NOT NULL,
    confidence      REAL DEFAULT 1.0,
    source          TEXT DEFAULT 'csv',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, symbol)
);

CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    TEXT NOT NULL DEFAULT 'default',
    symbol          TEXT NOT NULL,
    txn_type        TEXT NOT NULL,
    quantity        REAL NOT NULL,
    price           REAL NOT NULL,
    total_value     REAL NOT NULL,
    txn_date        DATE NOT NULL,
    source          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_cache (
    symbol          TEXT PRIMARY KEY,
    price           REAL NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'INR',
    change_pct      REAL,
    fetched_at      TIMESTAMP NOT NULL,
    source          TEXT DEFAULT 'yfinance'
);

CREATE TABLE IF NOT EXISTS price_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    date            DATE NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL NOT NULL,
    volume          REAL,
    UNIQUE(symbol, date)
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    TEXT NOT NULL DEFAULT 'default',
    snapshot_date   DATE NOT NULL,
    total_value     REAL,
    total_invested  REAL,
    total_pnl       REAL,
    sharpe_ratio    REAL,
    volatility      REAL,
    max_drawdown    REAL,
    beta            REAL,
    health_score    REAL,
    computed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol              TEXT NOT NULL,
    predicted_at        TIMESTAMP NOT NULL,
    horizon_days        INTEGER NOT NULL,
    predicted_price     REAL NOT NULL,
    confidence_high     REAL,
    confidence_low      REAL,
    model_used          TEXT,
    reliability_score   REAL,
    UNIQUE(symbol, horizon_days)
);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    TEXT NOT NULL DEFAULT 'default',
    alert_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    message         TEXT NOT NULL,
    triggered_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS instrument_master (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT UNIQUE NOT NULL,
    name            TEXT,
    exchange        TEXT,
    currency        TEXT DEFAULT 'INR',
    sector          TEXT,
    last_price      REAL,
    last_updated    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS symbol_aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_input       TEXT NOT NULL,
    resolved_symbol TEXT NOT NULL,
    confidence      REAL NOT NULL,
    source          TEXT,
    use_count       INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(raw_input)
);

CREATE INDEX IF NOT EXISTS idx_holdings_portfolio
    ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_price_history_symbol
    ON price_history(symbol, date);
CREATE INDEX IF NOT EXISTS idx_price_cache_fetched
    ON price_cache(fetched_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio
    ON metric_snapshots(portfolio_id, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol
    ON transactions(symbol, txn_date);
CREATE INDEX IF NOT EXISTS idx_instrument_master_symbol
    ON instrument_master(symbol);
CREATE INDEX IF NOT EXISTS idx_symbol_aliases_raw
    ON symbol_aliases(raw_input);
"""


def run_migrations():
    """Create all tables if they don't exist."""
    try:
        conn = get_connection()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        logger.info("✅ Database migrations complete")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise