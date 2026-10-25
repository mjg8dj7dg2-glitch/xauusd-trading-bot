from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from engines.paper_history import PaperHistoryAnalyzer


def create_test_database(db_path: Path):
    connection = sqlite3.connect(str(db_path))

    connection.execute("""
        CREATE TABLE paper_sessions (
            session_id TEXT PRIMARY KEY,
            strategy_name TEXT,
            status TEXT,
            initial_balance REAL,
            final_balance REAL,
            started_at TEXT,
            finished_at TEXT,
            metadata_json TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            trade_id TEXT,
            timestamp TEXT,
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            stop_loss REAL,
            take_profit REAL,
            quantity REAL,
            pnl REAL,
            result TEXT,
            strategy_name TEXT,
            regime TEXT,
            volatility_regime TEXT,
            memory_summary_json TEXT,
            metadata_json TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE paper_equity_curve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT,
            equity REAL,
            balance REAL,
            drawdown REAL,
            metadata_json TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE paper_monitor_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT,
            status TEXT,
            safe INTEGER,
            review_required INTEGER,
            metrics_json TEXT,
            reasons_json TEXT,
            warnings_json TEXT,
            thresholds_json TEXT,
            metadata_json TEXT
        )
    """)

    connection.execute("""
        INSERT INTO paper_sessions
        VALUES (
            'SESSION_A',
            'TEST_STRATEGY',
            'FINISHED',
            10000.0,
            10125.0,
            '2026-01-01T00:00:00+00:00',
            '2026-01-01T01:00:00+00:00',
            '{}'
        )
    """)

    connection.execute("""
        INSERT INTO paper_sessions
        VALUES (
            'SESSION_B',
            'TEST_STRATEGY',
            'FINISHED',
            10000.0,
            9950.0,
            '2026-01-02T00:00:00+00:00',
            '2026-01-02T01:00:00+00:00',
            '{}'
        )
    """)

    trades = [
        (
            "SESSION_A",
            "A1",
            "LONG",
            100.0,
            "WIN",
            "TRENDING_UP",
            "LOW",
        ),
        (
            "SESSION_A",
            "A2",
            "LONG",
            50.0,
            "WIN",
            "TRENDING_UP",
            "NORMAL",
        ),
        (
            "SESSION_A",
            "A3",
            "SHORT",
            -25.0,
            "LOSS",
            "TRENDING_DOWN",
            "LOW",
        ),
        (
            "SESSION_B",
            "B1",
            "SHORT",
            -30.0,
            "LOSS",
            "TRENDING_DOWN",
            "LOW",
        ),
        (
            "SESSION_B",
            "B2",
            "SHORT",
            -20.0,
            "LOSS",
            "TRENDING_DOWN",
            "LOW",
        ),
        (
            "SESSION_B",
            "B3",
            "LONG",
            0.0,
            "BREAKEVEN",
            "TRENDING_UP",
            "NORMAL",
        ),
    ]

    for (
        session_id,
        trade_id,
        direction,
        pnl,
        result,
        regime,
        volatility,
    ) in trades:

        connection.execute(
            """
            INSERT INTO paper_trades (
                session_id,
                trade_id,
                timestamp,
                direction,
                pnl,
                result,
                strategy_name,
                regime,
                volatility_regime
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                trade_id,
                "2026-01-01T00:00:00+00:00",
                direction,
                pnl,
                result,
                "TEST_STRATEGY",
                regime,
                volatility,
            ),
        )

    equity_points = [
        (
            "SESSION_A",
            "2026-01-01T00:00:00+00:00",
            10000.0,
        ),
        (
            "SESSION_A",
            "2026-01-01T00:10:00+00:00",
            10100.0,
        ),
        (
            "SESSION_A",
            "2026-01-01T00:20:00+00:00",
            10050.0,
        ),
        (
            "SESSION_A",
            "2026-01-01T00:30:00+00:00",
            10125.0,
        ),
        (
            "SESSION_B",
            "2026-01-02T00:00:00+00:00",
            10000.0,
        ),
        (
            "SESSION_B",
            "2026-01-02T00:10:00+00:00",
            9970.0,
        ),
        (
            "SESSION_B",
            "2026-01-02T00:20:00+00:00",
            9950.0,
        ),
    ]

    for session_id, timestamp, equity in equity_points:
        connection.execute(
            """
            INSERT INTO paper_equity_curve (
                session_id,
                timestamp,
                equity,
                balance
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                timestamp,
                equity,
                equity,
            ),
        )

    connection.execute(
        """
        INSERT INTO paper_monitor_snapshots (
            session_id,
            timestamp,
            status,
            safe,
            review_required
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "SESSION_A",
            "2026-01-01T01:00:00+00:00",
            "ACTIVE",
            1,
            0,
        ),
    )

    connection.execute(
        """
        INSERT INTO paper_monitor_snapshots (
            session_id,
            timestamp,
            status,
            safe,
            review_required
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "SESSION_B",
            "2026-01-02T01:00:00+00:00",
            "REVIEW",
            0,
            1,
        ),
    )

    connection.commit()
    connection.close()


def main():
    print()
    print("PAPER HISTORY ANALYZER TEST")
    print("============================")

    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "paper_history_test.db"

    try:
        create_test_database(db_path)

        analyzer = PaperHistoryAnalyzer(db_path)

        report = analyzer.analyze(
            strategy_name="TEST_STRATEGY"
        )

        assert report["sessions_analyzed"] == 2
        print("PASS: multiple sessions loaded")

        assert report["aggregate"]["trades"] == 6
        print("PASS: aggregate trade count")

        assert report["aggregate"]["wins"] == 2
        assert report["aggregate"]["losses"] == 3
        print("PASS: aggregate wins and losses")

        # SESSION A = +125
        # SESSION B = -50
        # TOTAL = +75
        assert abs(
            report["aggregate"]["pnl"] - 75.0
        ) < 1e-9

        print("PASS: aggregate P&L")

        assert (
            abs(
                report["aggregate"]["win_rate"]
                - (2 / 6)
            )
            < 1e-9
        )

        print("PASS: aggregate win rate")

        assert (
            report["sessions"][0]["session_id"]
            == "SESSION_B"
        )

        print("PASS: sessions sorted newest first")

        session_a = next(
            item
            for item in report["sessions"]
            if item["session_id"] == "SESSION_A"
        )

        assert session_a["wins"] == 2
        assert session_a["losses"] == 1
        assert session_a["pnl"] == 125.0

        print("PASS: session A performance")

        session_b = next(
            item
            for item in report["sessions"]
            if item["session_id"] == "SESSION_B"
        )

        assert (
            session_b["longest_losing_streak"]
            == 2
        )

        print("PASS: losing streak detection")

        assert (
            session_b["latest_monitor"]["status"]
            == "REVIEW"
        )

        print("PASS: latest monitor state")

        assert (
            report["historical_status"]
            == "REVIEW_HISTORY"
        )

        print("PASS: historical review state")

        assert (
            "TRENDING_UP"
            in session_a["trend_regime"]
        )

        assert (
            "TRENDING_DOWN"
            in session_b["trend_regime"]
        )

        print("PASS: trend-regime analysis")

        assert (
            "LOW"
            in session_a["volatility_regime"]
        )

        assert (
            "NORMAL"
            in session_a["volatility_regime"]
        )

        print("PASS: volatility-regime analysis")

        expected_drawdown_a = (
            50.0 / 10100.0
        )

        assert abs(
            session_a["max_drawdown"]
            - expected_drawdown_a
        ) < 1e-9

        print("PASS: drawdown calculation")

        filtered = analyzer.analyze(
            strategy_name="DOES_NOT_EXIST"
        )

        assert (
            filtered["sessions_analyzed"] == 0
        )

        assert (
            filtered["historical_status"]
            == "INSUFFICIENT_DATA"
        )

        print("PASS: empty strategy history")

    finally:
        for suffix in ("", "-wal", "-shm"):
            file_path = Path(
                str(db_path) + suffix
            )

            try:
                if file_path.exists():
                    file_path.unlink()
            except PermissionError:
                pass

        try:
            Path(temp_dir).rmdir()
        except OSError:
            pass

    print()
    print("PAPER HISTORY ANALYZER TEST PASSED")


if __name__ == "__main__":
    main()