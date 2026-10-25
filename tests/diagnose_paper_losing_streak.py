from collections import Counter
from pathlib import Path
import tempfile

from engines.paper_persistence import PaperPersistence
from engines.paper_runner import PaperTradingRunner

DATA_FILE = Path("data") / "xauusd" / "raw" / "XAUUSD_5m.csv"
THRESHOLD = 5


def pnl_of(trade):
    try:
        return float(trade.get("pnl", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def losing_streaks(trades):
    current = []
    best = []

    for index, trade in enumerate(trades, start=1):
        if pnl_of(trade) < 0:
            current.append((index, trade, pnl_of(trade)))
            if len(current) > len(best):
                best = current.copy()
        else:
            current = []

    return best


def main():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"CSV not found: {DATA_FILE}")

    with tempfile.TemporaryDirectory(
        prefix="paper_losing_streak_diagnostic_"
    ) as temp_dir:
        db_path = Path(temp_dir) / "diagnostic_only.db"
        persistence = PaperPersistence(db_path)

        runner = PaperTradingRunner(
            initial_balance=10000.0,
            risk_per_trade=0.01,
            stop_atr_multiplier=2.0,
            take_profit_ratio=2.0,
            strategy_name="XAUUSD_PAPER_DIAGNOSTIC",
            persistence=persistence,
        )

        result = runner.run(DATA_FILE)
        report = result.get("paper_report")

        if not isinstance(report, dict):
            raise RuntimeError("No valid paper report; refusing analysis.")
        if report.get("mode") != "PAPER":
            raise RuntimeError("Report mode is not exactly PAPER.")
        if report.get("live_trading") is not False:
            raise RuntimeError("live_trading is not exactly False.")
        if report.get("status") != "COMPLETE":
            raise RuntimeError("Paper report did not complete.")

        trades = report.get("trades", [])
        best = losing_streaks(trades)

        print("\n=== LOSING-STREAK DIAGNOSTIC ===")
        print("Mode:", report.get("mode"))
        print("Live trading:", report.get("live_trading"))
        print("Report status:", report.get("status"))
        print("Trade count:", len(trades))
        print("Losing-streak review threshold:", THRESHOLD)
        print("Maximum consecutive losses:", len(best))

        if best:
            total = sum(item[2] for item in best)
            print("Streak trade indices:", best[0][0], "to", best[-1][0])
            print(f"Streak combined P&L: {total:.2f}")
            print("Trades in longest losing streak:")
            for index, trade, pnl in best:
                print(
                    f"  #{index}: pnl={pnl:.2f}, "
                    f"direction={trade.get('direction', trade.get('signal', 'UNKNOWN'))}, "
                    f"entry={trade.get('entry_time', trade.get('entry_timestamp', 'UNKNOWN'))}, "
                    f"exit={trade.get('exit_time', trade.get('exit_timestamp', 'UNKNOWN'))}, "
                    f"reason={trade.get('exit_reason', trade.get('reason', 'UNKNOWN'))}"
                )

        print("\n=== EVALUATION ===")
        print("Paper evaluation:", result.get("paper_evaluation"))

        events = runner.session.get_risk_events()
        print("\n=== PERSISTED RISK EVENTS ===")
        print("Risk-event count:", len(events))
        event_types = Counter(
            str(event.get("event_type") or "UNKNOWN") for event in events
        )
        reasons = Counter(
            str(event.get("reason") or "NO REASON RECORDED") for event in events
        )
        print("Event types:", dict(event_types))
        print("Reasons:", dict(reasons))
        print("First five risk events:")
        for event in events[:5]:
            print({
                key: event.get(key)
                for key in ("timestamp", "event_type", "allowed", "reason")
            })

        print("\nTemporary database exists during run:", db_path.exists())
        print("Production database was not passed to the runner.")

    print("Temporary diagnostic directory cleaned up.")


if __name__ == "__main__":
    main()
