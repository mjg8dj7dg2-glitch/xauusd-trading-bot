
from pathlib import Path
import tempfile

from engines.paper_persistence import PaperPersistence
from engines.paper_runner import PaperTradingRunner

DATA_FILE = Path("data") / "xauusd" / "raw" / "XAUUSD_5m.csv"


def main():
    assert DATA_FILE.exists(), f"Missing CSV: {DATA_FILE}"

    with tempfile.TemporaryDirectory(
        prefix="paper_runner_isolated_"
    ) as temp_dir:
        test_db = Path(temp_dir) / "paper_test.db"
        persistence = PaperPersistence(test_db)

        runner = PaperTradingRunner(
            initial_balance=10000.0,
            risk_per_trade=0.01,
            stop_atr_multiplier=2.0,
            take_profit_ratio=2.0,
            strategy_name="XAUUSD_PAPER_ISOLATED_TEST",
            persistence=persistence,
        )

        result = runner.run(DATA_FILE)

        assert result["session_id"]
        assert result["strategy_name"] == "XAUUSD_PAPER_ISOLATED_TEST"
        assert result["pipeline"]["data"] is not None
        assert not result["pipeline"]["data"].empty

        report = result["paper_report"]
        assert report["mode"] == "PAPER"
        assert report["live_trading"] is False
        assert report["status"] == "COMPLETE"
        assert result["session"]["status"] == "FINISHED"

        counts = result["record_counts"]
        assert counts["paper_sessions"] >= 1
        assert counts["paper_trades"] >= 0
        assert counts["paper_equity_curve"] >= 0
        assert counts["paper_risk_events"] >= 0
        assert counts["paper_monitor_snapshots"] >= 1

        assert test_db.exists()
        print("PASS: isolated paper runner completed")
        print("PASS: persisted records verified in temporary database")

    print("PASS: temporary database directory cleaned up")


if __name__ == "__main__":
    main()
