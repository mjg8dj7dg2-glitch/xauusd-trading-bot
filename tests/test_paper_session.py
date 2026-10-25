import gc
import shutil
import tempfile
import time
from pathlib import Path

from engines.paper_persistence import PaperPersistence
from engines.paper_session import PaperTradingSession


def main():
    print("\nPAPER TRADING SESSION TEST\n")

    temp_dir = tempfile.mkdtemp(prefix="paper_session_test_")
    db_path = Path(temp_dir) / "paper_session_test.db"
    session = None

    try:
        persistence = PaperPersistence(db_path)
        session = PaperTradingSession(
            persistence=persistence,
            session_id="TEST_SESSION",
        )

        session.start(initial_balance=10000)
        print("PASS: session started")

        report = {
            "status": "COMPLETED",
            "performance": {
                "initial_balance": 10000,
                "final_balance": 10100,
            },
            "trades": [
                {
                    "symbol": "TEST",
                    "side": "BUY",
                    "quantity": 1,
                    "entry_price": 100,
                    "exit_price": 110,
                    "pnl": 10,
                },
                {
                    "symbol": "TEST",
                    "side": "SELL",
                    "quantity": 1,
                    "entry_price": 110,
                    "exit_price": 105,
                    "pnl": -5,
                },
                {
                    "symbol": "TEST",
                    "side": "BUY",
                    "quantity": 1,
                    "entry_price": 100,
                    "exit_price": 105,
                    "pnl": 5,
                },
            ],
            "equity_curve": [
                {"timestamp": "test-1", "equity": 10000},
                {"timestamp": "test-2", "equity": 10100},
            ],
            "risk_events": [
                {
                    "event_type": "TEST_BLOCKED",
                    "allowed": False,
                    "reason": "Test risk event",
                }
            ],
        }

        session.save_report(report)
        print("PASS: report processed")

        saved_session = persistence.get_session(session.session_id)
        assert saved_session is not None, "Session was not persisted"
        print("PASS: session persisted")

        trades = session.get_trades()
        assert len(trades) == 3, (
            f"Expected 3 trades, found {len(trades)}"
        )
        print("PASS: trades persisted")

        risk_events = session.get_risk_events()
        assert risk_events, "No risk events were persisted"

        blocked_events = [
            event
            for event in risk_events
            if event.get("event_type") == "TEST_BLOCKED"
        ]
        assert blocked_events, "TEST_BLOCKED event was not found"
        assert blocked_events[0].get("allowed") in (False, 0), (
            "Blocked event did not persist allowed=False"
        )
        print("PASS: risk events persisted")

        test_snapshot = {
            "status": "TEST",
            "message": "Monitor persistence test",
        }

        session.finish(monitor_snapshot=test_snapshot)
        print("PASS: session finished with monitor snapshot")

        assert session.latest_monitor_snapshot == test_snapshot, (
            "Monitor snapshot was not saved in the session"
        )

        saved_snapshots = session.get_monitor_history()
        assert saved_snapshots, "No monitor snapshot history was saved"
        print("PASS: monitor snapshot history persisted")

        counts = persistence.get_record_counts()
        assert counts, "Record counts were not returned"
        print("PASS: record counts available")

        print("\nPAPER TRADING SESSION TEST PASSED")

    finally:
        session = None
        gc.collect()

        for attempt in range(10):
            try:
                shutil.rmtree(temp_dir)
                break
            except PermissionError:
                gc.collect()
                time.sleep(0.2)
        else:
            print(
                "WARNING: Could not remove the temporary test directory: "
                f"{temp_dir}"
            )


if __name__ == "__main__":
    main()