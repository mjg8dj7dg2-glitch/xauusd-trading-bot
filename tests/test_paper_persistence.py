import json
import tempfile
from pathlib import Path
from engines.paper_persistence import PaperPersistence

def test_persistence():
    with tempfile.TemporaryDirectory(prefix="paper_test_", ignore_cleanup_errors=True) as d:
        db = PaperPersistence(Path(d) / "test.db")
        sid = "isolated_test"
        db.ensure_tables()
        db.create_session(sid, strategy_name="TEST", initial_balance=10000)
        assert db.save_trades(sid, [{"trade_id": "T1", "pnl": 1}, {"trade_id": "T2", "pnl": 2}, {"trade_id": "T3", "pnl": 3}]) == 3
        assert db.save_equity_curve(sid, [10000, 10001, 10002]) == 3
        events = [{"event_type": "TEST", "allowed": True}, {"event_type": "TEST", "allowed": False}, {"event_type": "TEST", "allowed": None}]
        assert db.save_risk_events(sid, events) == 3
        db.save_monitor_snapshot(sid, {"status": "OK", "safe": True})
        counts = db.count_records(sid)
        assert counts["paper_sessions"] == 1 and counts["paper_trades"] == 3 and counts["paper_equity_curve"] == 3 and counts["paper_risk_events"] == 3 and counts["paper_monitor_snapshots"] == 1, counts
        saved = db.get_risk_events(sid)
        assert [e["allowed"] for e in saved] == [1, 0, None], saved
        print("PASS: persistence counts are correct.")
        print("PASS: allowed True, False, and None persist as 1, 0, and NULL.")
        print(json.dumps(counts, indent=2))

if __name__ == "__main__":
    test_persistence()
