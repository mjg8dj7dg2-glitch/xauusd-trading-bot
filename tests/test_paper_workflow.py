from __future__ import annotations

from datetime import datetime, timedelta
import tempfile
from pathlib import Path

import pandas as pd

from engines.paper_persistence import PaperPersistence
from engines.paper_session import PaperTradingSession
from engines.paper_trading import PaperTradingEngine


def build_test_data(periods: int = 80) -> pd.DataFrame:
    timestamps = [
        datetime(2026, 1, 1) + timedelta(minutes=5 * i)
        for i in range(periods)
    ]

    close_prices = [100.0 + (i * 0.10) for i in range(periods)]

    data = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close_prices,
            "high": [price + 0.20 for price in close_prices],
            "low": [price - 0.20 for price in close_prices],
            "close": close_prices,
            "volume": [1000] * periods,
        }
    )

    data["signal"] = "NO_SIGNAL"

    for i in range(10, periods, 15):
        data.loc[i, "signal"] = "LONG"

    data["volatility_regime"] = "NORMAL"
    data["trend_regime"] = "TRENDING_UP"
    data["atr"] = [0.50] * periods

    return data


def main(db_path: str | Path):
    print()
    print("=" * 80)
    print("PAPER WORKFLOW INTEGRATION TEST")
    print("=" * 80)

    data = build_test_data()

    print("PASS: test market data created")

    valid_signals = {"LONG", "SHORT", "NO_SIGNAL"}
    assert set(data["signal"].unique()).issubset(valid_signals)

    print("PASS: signal values are valid")

    assert "volatility_regime" in data.columns
    assert "trend_regime" in data.columns
    assert "atr" in data.columns

    print("PASS: regime and volatility fields are present")

    engine = PaperTradingEngine(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
    )

    report = engine.run(
        data,
        strategy_name="WORKFLOW_TEST",
    )

    assert report["mode"] == "PAPER"
    assert report["live_trading"] is False
    assert report["status"] == "COMPLETE"

    print("PASS: paper engine completed")

    assert "performance" in report
    assert "account" in report
    assert "risk" in report

    print("PASS: paper performance generated")

    persistence = PaperPersistence(db_path)

    session = PaperTradingSession(
        persistence=persistence,
        strategy_name="WORKFLOW_TEST",
        metadata={
            "test": True,
            "purpose": "paper workflow integration test",
        },
    )

    session_id = session.start(
        initial_balance=10000.0
    )

    assert session_id
    assert session.get_session() is not None

    processed = session.process_report(
        report,
        run_monitor=True,
    )

    assert processed["status"] == "COMPLETE"

    print("PASS: paper report processed")

    saved_session = session.get_session()

    assert saved_session is not None
    assert saved_session["session_id"] == session_id

    print("PASS: paper session persisted")

    trades = session.get_trades()
    assert isinstance(trades, list)

    print("PASS: trades persisted")

    equity_curve = session.persistence.get_equity_curve(
        session_id
    )

    assert isinstance(equity_curve, list)

    print("PASS: equity curve persisted")

    risk_events = session.get_risk_events()

    assert isinstance(risk_events, list)

    print("PASS: risk events persisted")

    monitor_snapshots = session.get_monitor_history()

    assert isinstance(monitor_snapshots, list)

    print("PASS: monitor snapshot persisted")

    counts = session.get_record_counts()

    assert counts["trades"] == len(trades)
    assert counts["equity_curve"] == len(equity_curve)
    assert counts["risk_events"] == len(risk_events)
    assert counts["monitor_snapshots"] == len(monitor_snapshots)

    print("PASS: all session record counts are correct")

    summary = session.get_summary()

    assert summary is not None
    assert summary["session_id"] == session_id

    print("PASS: session summary works")

    session.finish()

    finished_session = session.get_session()

    assert finished_session is not None
    assert finished_session["status"] == "FINISHED"

    print("PASS: session finished")

    print()
    print("=" * 80)
    print("PAPER WORKFLOW INTEGRATION TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="paper_workflow_test_") as temp_dir:
        main(Path(temp_dir) / "workflow_test.db")