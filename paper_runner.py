from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from engines.pipeline import TradingPipeline
from engines.paper_monitor import PaperTradingMonitor
from engines.paper_session import PaperTradingSession


class PaperTradingRunner:
    """
    Repeatable paper-trading runner.

    Flow:
        CSV
        -> TradingPipeline
        -> analyzed market data
        -> PaperTradingSession
        -> PaperTradingEngine
        -> persistent paper session
    """

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        risk_per_trade: float = 0.01,
        stop_atr_multiplier: float = 2.0,
        take_profit_ratio: float = 2.0,
        commission_per_trade: float = 0.0,
        slippage_per_trade: float = 0.0,
        strategy_name: str = "PAPER_STRATEGY",
        persistence=None,
    ):
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.stop_atr_multiplier = stop_atr_multiplier
        self.take_profit_ratio = take_profit_ratio
        self.commission_per_trade = commission_per_trade
        self.slippage_per_trade = slippage_per_trade
        self.strategy_name = strategy_name
        self.persistence = persistence

    def run(
        self,
        file_path: str | Path,
    ) -> dict[str, Any]:
        """
        Run one complete paper-trading session.

        Returns the persisted session result.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Market data file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Market data path is not a file: {path}"
            )

        print()
        print("=" * 80)
        print("PAPER TRADING RUNNER")
        print("=" * 80)

        print()
        print(f"Market data: {path}")
        print(f"Strategy: {self.strategy_name}")
        print(f"Initial balance: {self.initial_balance:,.2f}")

        # ---------------------------------------------------------
        # 1. Run the existing market-analysis pipeline.
        # ---------------------------------------------------------

        print()
        print("[1/4] Running market analysis pipeline...")

        pipeline = TradingPipeline(
            initial_balance=self.initial_balance,
            risk_per_trade=self.risk_per_trade,
            stop_atr_multiplier=self.stop_atr_multiplier,
            take_profit_ratio=self.take_profit_ratio,
            commission_per_trade=self.commission_per_trade,
            slippage_per_trade=self.slippage_per_trade,
        )

        pipeline_result = pipeline.run(
            str(path)
        )

        analyzed_data = pipeline_result["data"]

        if analyzed_data is None:
            raise ValueError(
                "Pipeline returned no analyzed market data."
            )

        if analyzed_data.empty:
            raise ValueError(
                "Pipeline returned empty analyzed market data."
            )

        print(
            f"PASS: pipeline analyzed "
            f"{len(analyzed_data):,} rows"
        )


        # ---------------------------------------------------------
        # 3. Run the paper engine against analyzed data.
        # ---------------------------------------------------------

        print()
        print("[3/4] Running paper trading simulation...")

        from engines.paper_trading import PaperTradingEngine

        paper_engine = PaperTradingEngine(
            initial_balance=self.initial_balance,
            risk_per_trade=self.risk_per_trade,
            stop_atr_multiplier=self.stop_atr_multiplier,
            take_profit_ratio=self.take_profit_ratio,
            commission_per_trade=self.commission_per_trade,
            slippage_per_trade=self.slippage_per_trade,
        )

        paper_report = paper_engine.run(
            analyzed_data,
            strategy_name=self.strategy_name,
        )

        if not isinstance(paper_report, dict):
            raise TypeError(
                "Paper trading engine must return a dictionary."
            )

        if paper_report.get("status") != "COMPLETE":
            raise RuntimeError(
                "Paper trading engine did not complete successfully."
            )

        if paper_report.get("mode") != "PAPER":
            raise RuntimeError(
                "Refusing to persist a report unless mode is exactly 'PAPER'."
            )

        if paper_report.get("live_trading") is not False:
            raise RuntimeError(
                "Refusing to persist a report unless live_trading is exactly False."
            )

        print(
            "PASS: paper trading simulation completed"
        )
        # ---------------------------------------------------------
        # 2. Create the persistent paper session.
        # ---------------------------------------------------------

        print()
        print("[2/4] Starting persistent paper session...")

        monitor = PaperTradingMonitor()

        session = PaperTradingSession(
            persistence=self.persistence,
            monitor=monitor,
            strategy_name=self.strategy_name,
            metadata={
                "market_data_file": str(path),
                "runner": "PaperTradingRunner",
                "initial_balance": self.initial_balance,
                "risk_per_trade": self.risk_per_trade,
                "stop_atr_multiplier": self.stop_atr_multiplier,
                "take_profit_ratio": self.take_profit_ratio,
            },
        )

        session.start(
            initial_balance=self.initial_balance
        )

        print(
            f"PASS: session started "
            f"{session.session_id}"
        )

        # ---------------------------------------------------------
        # 4. Persist the report and monitor the session.
        # ---------------------------------------------------------

        print()
        print("[4/4] Persisting report and monitoring session...")

        processed = session.process_report(
            paper_report,
            run_monitor=True,
        )

        session.finish()

        print(
            "PASS: report persisted and session finished"
        )

        # ---------------------------------------------------------
        # Build a useful runner result.
        # ---------------------------------------------------------

        final_session = session.get_session()
        summary = session.get_summary()
        counts = session.get_record_counts()

        result = {
            "session_id": session.session_id,
            "strategy_name": self.strategy_name,
            "market_data_file": str(path),
            "pipeline": pipeline_result,
            "paper_report": paper_report,
            "processed": processed,
            "session": final_session,
            "summary": summary,
            "record_counts": counts,
        }

        self._print_summary(
            result
        )

        return result

    def _print_summary(
        self,
        result: dict[str, Any],
    ) -> None:
        report = result["paper_report"]

        account = report.get(
            "account",
            {},
        )

        performance = report.get(
            "performance",
            {},
        )

        risk = report.get(
            "risk",
            {},
        )

        print()
        print("=" * 80)
        print("PAPER TRADING SESSION SUMMARY")
        print("=" * 80)

        print()
        print(
            f"Session ID:        "
            f"{result['session_id']}"
        )

        print(
            f"Strategy:          "
            f"{result['strategy_name']}"
        )

        print(
            f"Initial balance:   "
            f"{account.get('initial_balance', 0.0):,.2f}"
        )

        print(
            f"Final balance:     "
            f"{account.get('final_balance', 0.0):,.2f}"
        )

        print(
            f"Max drawdown:      "
            f"{account.get('max_drawdown', 0.0):.2%}"
        )

        print(
            f"Trades:            "
            f"{performance.get('trades', 0)}"
        )

        print(
            f"Winning trades:    "
            f"{performance.get('wins', 0)}"
        )

        print(
            f"Losing trades:     "
            f"{performance.get('losses', 0)}"
        )

        print(
            f"Win rate:          "
            f"{performance.get('win_rate', 0.0):.2%}"
        )

        print(
            f"Profit factor:     "
            f"{performance.get('profit_factor', 0.0):.4f}"
        )

        print(
            f"P&L:               "
            f"{performance.get('pnl', 0.0):,.2f}"
        )

        print(
            f"Allowed entries:   "
            f"{risk.get('allowed_entries', 0)}"
        )

        print(
            f"Blocked entries:   "
            f"{risk.get('blocked_entries', 0)}"
        )

        print(
            f"Risk events:       "
            f"{risk.get('risk_event_count', 0)}"
        )

        counts = result["record_counts"]

        print()
        print("Persisted records:")
        print(
            f"  Sessions:         "
            f"{counts.get('paper_sessions', 0)}"
        )
        print(
            f"  Trades:           "
            f"{counts.get('paper_trades', 0)}"
        )
        print(
            f"  Equity points:    "
            f"{counts.get('paper_equity_curve', 0)}"
        )
        print(
            f"  Risk events:      "
            f"{counts.get('paper_risk_events', 0)}"
        )
        print(
            f"  Monitor snapshots: "
            f"{counts.get('paper_monitor_snapshots', 0)}"
        )

        print()
        print("=" * 80)
        print("PAPER TRADING RUN COMPLETE")
        print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a repeatable paper-trading session."
    )

    parser.add_argument(
        "file_path",
        help="Path to the market-data CSV file.",
    )

    parser.add_argument(
        "--strategy",
        default="PAPER_STRATEGY",
        help="Strategy name.",
    )

    parser.add_argument(
        "--balance",
        type=float,
        default=10_000.0,
        help="Initial paper balance.",
    )

    parser.add_argument(
        "--risk",
        type=float,
        default=0.01,
        help="Risk per trade as a decimal.",
    )

    parser.add_argument(
        "--stop-atr",
        type=float,
        default=2.0,
        help="ATR multiplier for stop distance.",
    )

    parser.add_argument(
        "--take-profit",
        type=float,
        default=2.0,
        help="Take-profit reward ratio.",
    )

    args = parser.parse_args()

    runner = PaperTradingRunner(
        initial_balance=args.balance,
        risk_per_trade=args.risk,
        stop_atr_multiplier=args.stop_atr,
        take_profit_ratio=args.take_profit,
        strategy_name=args.strategy,
    )

    runner.run(
        args.file_path
    )


if __name__ == "__main__":
    main()