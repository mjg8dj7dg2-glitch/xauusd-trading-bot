import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "trading_bot.db"


def get_connection():
    """Create a connection to the trading bot database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create all tables required by the trading bot."""

    connection = get_connection()

    connection.executescript("""
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            instrument TEXT,
            timeframe TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS strategy_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            version TEXT NOT NULL,
            parameters TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        );

        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL,
            UNIQUE(instrument, timeframe, timestamp)
        );

        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            strategy_version_id INTEGER,
            instrument TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            direction TEXT,
            signal_strength REAL,
            reason TEXT,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id),
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions(id)
        );

        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            quantity REAL,
            pnl REAL,
            result TEXT,
            entry_time TEXT,
            exit_time TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );

        CREATE TABLE IF NOT EXISTS trade_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER NOT NULL,
            trend_regime TEXT,
            volatility_regime TEXT,
            rsi REAL,
            atr REAL,
            ema_fast REAL,
            ema_slow REAL,
            market_correlation REAL,
            macro_context TEXT,
            news_context TEXT,
            mae REAL,
            mfe REAL,
            failure_reason TEXT,
            FOREIGN KEY (trade_id) REFERENCES trades(id)
        );

        CREATE TABLE IF NOT EXISTS market_regimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            trend_regime TEXT,
            volatility_regime TEXT,
            confidence REAL
        );

        CREATE TABLE IF NOT EXISTS news_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT NOT NULL,
            event_name TEXT NOT NULL,
            currency TEXT,
            previous_value REAL,
            forecast_value REAL,
            actual_value REAL,
            surprise REAL,
            impact TEXT
        );

        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            strategy_version_id INTEGER,
            instrument TEXT,
            timeframe TEXT,
            start_date TEXT,
            end_date TEXT,
            initial_balance REAL,
            final_balance REAL,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            win_rate REAL,
            profit_factor REAL,
            max_drawdown REAL,
            sharpe_ratio REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id),
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions(id)
        );

        CREATE TABLE IF NOT EXISTS health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            strategy_version_id INTEGER,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            win_rate REAL,
            profit_factor REAL,
            max_drawdown REAL,
            average_trade REAL,
            recent_trade_count INTEGER,
            baseline_trade_count INTEGER,
            reason TEXT,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id),
            FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions(id)
        );

        CREATE TABLE IF NOT EXISTS risk_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            instrument TEXT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            action TEXT
        );

        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL
        );
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Trading bot database initialized successfully.")