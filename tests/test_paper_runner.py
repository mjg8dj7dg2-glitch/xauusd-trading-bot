from __future__ import annotations

from pathlib import Path

from engines.paper_runner import PaperTradingRunner


DATA_FILE = (
    Path("data")
    / "xauusd"
    / "raw"
    / "XAUUSD_5m.csv"
)


def main() -> None:
    print()
    print("=" * 80)
    print("PAPER TRADING RUNNER TEST")
    print("=" * 80)

    assert DATA_FILE.exists(), (
        f"Expected XAUUSD data file does not exist: "
        f"{DATA_FILE}"
    )

    runner = PaperTradingRunner(
        initial_balance=10_000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        strategy_name="XAUUSD_PAPER_TEST",
    )

    result = runner.run(
        DATA_FILE
    )

    assert result["session_id"]
    assert result["strategy_name"] == "XAUUSD_PAPER_TEST"

    assert result["pipeline"]["data"] is not None
    assert not result["pipeline"]["data"].empty

    paper_report = result["paper_report"]

    assert paper_report["mode"] == "PAPER"
    assert paper_report["live_trading"] is False
    assert paper_report["status"] == "COMPLETE"

    assert "performance" in paper_report
    assert "account" in paper_report
    assert "risk" in paper_report

    session = result["session"]

    assert session is not None
    assert session["status"] == "FINISHED"

    counts = result["record_counts"]

    assert counts["paper_sessions"] >= 1
    assert counts["paper_trades"] >= 0
    assert counts["paper_equity_curve"] >= 0
    assert counts["paper_risk_events"] >= 0
    assert counts["paper_monitor_snapshots"] >= 1

    print()
    print("PASS: XAUUSD data file found")
    print("PASS: pipeline completed")
    print("PASS: paper report completed")
    print("PASS: paper session persisted")
    print("PASS: session finished")
    print("PASS: persisted record counts are valid")

    print()
    print("=" * 80)
    print("PAPER TRADING RUNNER TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()