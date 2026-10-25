from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from engines.pipeline import TradingPipeline
from engines.paper_trading import PaperTradingEngine
from engines.paper_session import PaperTradingSession
from engines.paper_monitor import PaperTradingMonitor
from engines.paper_evaluation import PaperSessionEvaluator
from engines.strategy_evaluation import StrategyEvaluationEngine


class PaperTradingRunner:
    """
    Historical paper-trading runner.

    Flow:

        CSV
          ↓
        TradingPipeline
          ↓
        analyzed market data
          ↓
        PaperTradingEngine
          ↓
        PaperTradingSession
          ↓
        persistence / monitoring
          ↓
        paper evaluation
          ↓
        unified strategy evaluation

    This runner is paper/historical only.
    It does not place live orders.
    """

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        strategy_name: str = "XAUUSD_PAPER_TEST",
        risk_per_trade: float = 0.01,
        stop_atr_multiplier: float = 2.0,
        take_profit_ratio: float = 2.0,
        commission_per_trade: float = 0.0,
        slippage_per_trade: float = 0.0,
        news_events=None,
        comparison_df=None,
        comparison_data=None,
        correlation_window: int = 20,
        maximum_absolute_correlation: float = 0.8,
        news_before_minutes: float = 30.0,
        news_after_minutes: float = 15.0,
        risk_engine=None,
        persistence=None,
        monitor=None,
        session_metadata=None,
    ) -> None:

        self.initial_balance = float(initial_balance)
        self.strategy_name = strategy_name

        self.pipeline = TradingPipeline()

        self.paper_engine = PaperTradingEngine(
            initial_balance=self.initial_balance,
            risk_per_trade=risk_per_trade,
            stop_atr_multiplier=stop_atr_multiplier,
            take_profit_ratio=take_profit_ratio,
            commission_per_trade=commission_per_trade,
            slippage_per_trade=slippage_per_trade,
            news_events=news_events,
            comparison_df=comparison_df,
            comparison_data=comparison_data,
            correlation_window=correlation_window,
            maximum_absolute_correlation=maximum_absolute_correlation,
            news_before_minutes=news_before_minutes,
            news_after_minutes=news_after_minutes,
            risk_engine=risk_engine,
        )

        # Always provide a monitor unless the caller explicitly
        # supplies another monitor implementation.
        if monitor is None:
            monitor = PaperTradingMonitor()

        self.session = PaperTradingSession(
            persistence=persistence,
            monitor=monitor,
            strategy_name=self.strategy_name,
            metadata=session_metadata,
        )

        self.paper_evaluator = PaperSessionEvaluator()
        self.strategy_evaluator = StrategyEvaluationEngine()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _status(
        value: Any,
        default: str = "UNKNOWN",
    ) -> str:

        if isinstance(value, str):
            return value

        if isinstance(value, dict):

            if value.get("status") is not None:
                return str(value["status"])

            if value.get("state") is not None:
                return str(value["state"])

        return default

    @staticmethod
    def _extract_robustness(
        pipeline_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract the robustness report if the pipeline provides one.

        If the pipeline does not currently attach walk-forward robustness,
        return an explicit insufficient-data report rather than inventing
        robustness statistics.
        """

        candidates = [
            pipeline_report.get("robustness"),
            pipeline_report.get("robustness_report"),
            pipeline_report.get("walk_forward_robustness"),
            pipeline_report.get("walk_forward"),
        ]

        evaluation = pipeline_report.get("evaluation")

        if isinstance(evaluation, dict):
            candidates.append(
                evaluation.get("robustness")
            )

        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate

        return {
            "status": "INSUFFICIENT_DATA",
            "validation_trades": 0,
            "validation_windows": 0,
            "average_pf": 0.0,
            "positive_window_ratio": 0.0,
            "maximum_drawdown": 0.0,
            "reason": (
                "No walk-forward robustness report was attached "
                "to the pipeline result."
            ),
        }

    @staticmethod
    def _extract_health_status(
        pipeline_report: Dict[str, Any],
    ) -> str:
        """
        Extract existing historical strategy-health status.
        """

        candidates = [
            pipeline_report.get("strategy_health"),
            pipeline_report.get("health"),
            pipeline_report.get("strategy_health_report"),
        ]

        for candidate in candidates:

            status = PaperTradingRunner._status(
                candidate,
                "",
            )

            if status:
                return status

        return "ACTIVE"

    @staticmethod
    def _extract_regime_report(
        pipeline_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract existing regime-health information.
        """

        candidates = [
            pipeline_report.get("regime_health"),
            pipeline_report.get("regimes"),
            pipeline_report.get("market_regime_health"),
        ]

        for candidate in candidates:

            if isinstance(candidate, dict):
                return candidate

        return {}

    @staticmethod
    def _extract_memory_report(
        pipeline_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract existing trade-memory information.
        """

        candidates = [
            pipeline_report.get("memory"),
            pipeline_report.get("memory_report"),
            pipeline_report.get("trade_memory"),
        ]

        for candidate in candidates:

            if isinstance(candidate, dict):
                return candidate

        return {}

    @staticmethod
    def _paper_health_status(
        paper_evaluation: Dict[str, Any],
    ) -> str:
        """
        Convert the paper-session evaluation into a health state
        understood by the unified evaluator.
        """

        status = PaperTradingRunner._status(
            paper_evaluation,
            "UNKNOWN",
        )

        if status in {
            "ACTIVE",
            "HEALTHY",
            "COMPLETE",
        }:
            return "ACTIVE"

        if status in {
            "REVIEW",
            "WARNING",
        }:
            return "REVIEW"

        if status in {
            "PAUSED",
            "FAILED",
        }:
            return "PAUSED"

        return status

    @staticmethod
    def _calculate_max_drawdown(
        equity_curve,
    ) -> float:
        """
        Calculate maximum percentage drawdown from an equity curve.

        Returns a positive decimal.

        Example:
            0.0568 == 5.68%
        """

        if equity_curve is None:
            return 0.0

        try:
            values = [
                float(value)
                for value in equity_curve
                if value is not None
            ]
        except (TypeError, ValueError):
            return 0.0

        if not values:
            return 0.0

        peak = values[0]
        maximum_drawdown = 0.0

        for value in values:

            if value > peak:
                peak = value

            if peak > 0:
                drawdown = (peak - value) / peak

                if drawdown > maximum_drawdown:
                    maximum_drawdown = drawdown

        return float(maximum_drawdown)

    # ------------------------------------------------------------------
    # Unified strategy health
    # ------------------------------------------------------------------

    def _build_unified_health(
        self,
        pipeline_report: Dict[str, Any],
        paper_report: Dict[str, Any],
        paper_evaluation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Connect the real XAUUSD paper run to the existing
        StrategyEvaluationEngine.
        """

        robustness_report = self._extract_robustness(
            pipeline_report
        )

        historical_health = self._extract_health_status(
            pipeline_report
        )

        regime_report = self._extract_regime_report(
            pipeline_report
        )

        memory_report = self._extract_memory_report(
            pipeline_report
        )

        paper_health = self._paper_health_status(
            paper_evaluation
        )

        paper_completed = (
            isinstance(paper_report, dict)
            and paper_report.get("mode") == "PAPER"
            and paper_report.get("live_trading") is False
        )

        paper_state = {
            "status": paper_health,
            "state": paper_health,
            "complete": paper_completed,
            "completed": paper_completed,
            "healthy": paper_health == "ACTIVE",
        }

        health_states = {
            self.strategy_name: historical_health
        }

        paper_states = {
            self.strategy_name: paper_state
        }

        regime_reports = {
            self.strategy_name: regime_report
        }

        memory_reports = {
            self.strategy_name: memory_report
        }

        currently_active = {
            self.strategy_name: (
                historical_health == "ACTIVE"
            )
        }

        # Include the paper evaluation explicitly so the unified
        # evaluator can use paper-session health information.
        paper_evaluations = {
            self.strategy_name: paper_evaluation
        }

        unified = self.strategy_evaluator.evaluate_all(
            robustness_report=robustness_report,
            paper_states=paper_states,
            health_states=health_states,
            regime_reports=regime_reports,
            paper_evaluations=paper_evaluations,
            memory_reports=memory_reports,
            currently_active=currently_active,
        )

        if not isinstance(unified, dict):
            unified = {
                "status": "INSUFFICIENT_DATA",
                "reason": (
                    "StrategyEvaluationEngine.evaluate_all() "
                    "did not return a dictionary."
                ),
            }

        # Keep the raw components available to the dashboard and
        # later reporting code.
        unified["strategy_name"] = self.strategy_name
        unified["historical_health"] = historical_health
        unified["paper_health"] = paper_health
        unified["paper_completed"] = paper_completed
        unified["robustness"] = robustness_report
        unified["regime_health"] = regime_report
        unified["memory"] = memory_report
        unified["paper_evaluation"] = paper_evaluation

        return unified

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _print_summary(
        self,
        paper_report: Dict[str, Any],
        paper_evaluation: Dict[str, Any],
        unified_health: Dict[str, Any],
        record_counts: Dict[str, Any],
    ) -> None:

        performance = paper_report.get(
            "performance",
            {},
        )

        account = paper_report.get(
            "account",
            {},
        )

        risk = paper_report.get(
            "risk",
            {},
        )

        equity_curve = paper_report.get(
            "equity_curve",
            [],
        )

        initial_balance = float(
            account.get(
                "initial_balance",
                self.initial_balance,
            )
        )

        # The paper engine's performance dictionary contains the
        # actual total P&L rather than final_balance.
        total_pnl = float(
            performance.get(
                "total_pnl",
                0.0,
            )
        )

        final_balance = initial_balance + total_pnl

        # Calculate drawdown from the actual persisted/generated
        # equity curve.
        max_drawdown = self._calculate_max_drawdown(
            equity_curve
        )

        trades = int(
            performance.get(
                "trades",
                len(
                    paper_report.get(
                        "trades",
                        [],
                    )
                ),
            )
        )

        wins = int(
            performance.get(
                "wins",
                0,
            )
        )

        losses = int(
            performance.get(
                "losses",
                0,
            )
        )

        win_rate = float(
            performance.get(
                "win_rate",
                0.0,
            )
        )

        profit_factor = float(
            performance.get(
                "profit_factor",
                0.0,
            )
        )

        # These are the actual keys returned by PaperTradingEngine.
        allowed = int(
            risk.get(
                "allowed_entries",
                0,
            )
        )

        blocked = int(
            risk.get(
                "blocked_entries",
                0,
            )
        )

        risk_events = int(
            risk.get(
                "risk_event_count",
                len(
                    paper_report.get(
                        "risk_events",
                        [],
                    )
                ),
            )
        )

        unified_status = self._status(
            unified_health,
            "UNKNOWN",
        )

        lifecycle_status = self._status(
            unified_health.get(
                "lifecycle"
            ),
            "UNKNOWN",
        )

        paper_status = self._status(
            paper_evaluation,
            "UNKNOWN",
        )

        print()
        print("=" * 80)
        print("PAPER TRADING SUMMARY")
        print("=" * 80)

        print(
            f"Strategy          {self.strategy_name}"
        )

        print(
            f"Mode              "
            f"{paper_report.get('mode', 'UNKNOWN')}"
        )

        print(
            f"Live trading      "
            f"{paper_report.get('live_trading', 'UNKNOWN')}"
        )

        print()

        print(
            f"Initial balance   "
            f"{initial_balance:,.2f}"
        )

        print(
            f"Final balance     "
            f"{final_balance:,.2f}"
        )

        print(
            f"P&L               "
            f"{total_pnl:+,.2f}"
        )

        print(
            f"Max DD            "
            f"{max_drawdown:.2%}"
        )

        print()

        print(
            f"Trades            "
            f"{trades}"
        )

        print(
            f"Wins              "
            f"{wins}"
        )

        print(
            f"Losses            "
            f"{losses}"
        )

        print(
            f"Win rate          "
            f"{win_rate:.2%}"
        )

        print(
            f"PF                "
            f"{profit_factor:.4f}"
        )

        print()

        print(
            f"Allowed           "
            f"{allowed}"
        )

        print(
            f"Blocked           "
            f"{blocked}"
        )

        print(
            f"Risk events       "
            f"{risk_events}"
        )

        print()

        print("STRATEGY HEALTH")

        print(
            f"Historical health "
            f"{unified_health.get('historical_health')}"
        )

        print(
            f"Lifecycle         "
            f"{lifecycle_status}"
        )

        print(
            f"Paper health      "
            f"{unified_health.get('paper_health')}"
        )

        print(
            f"Unified status    "
            f"{unified_status}"
        )

        print()

        print(
            "Persisted records "
            f"Sessions "
            f"{record_counts.get('paper_sessions', 0)}, "
            f"Trades "
            f"{record_counts.get('paper_trades', 0)}, "
            f"Equity points "
            f"{record_counts.get('paper_equity_curve', 0)}, "
            f"Risk events "
            f"{record_counts.get('paper_risk_events', 0)}, "
            f"Monitor snapshots "
            f"{record_counts.get('paper_monitor_snapshots', 0)}"
        )

        print()

        print(
            f"Paper evaluation: "
            f"{paper_status}"
        )

        reasons = paper_evaluation.get(
            "reasons",
            [],
        )

        if isinstance(reasons, list):

            for reason in reasons:
                print(
                    f"  - {reason}"
                )

        warnings = paper_evaluation.get(
            "warnings",
            [],
        )

        if isinstance(warnings, list):

            for warning in warnings:
                print(
                    f"  - WARNING: {warning}"
                )

        print("=" * 80)

    # ------------------------------------------------------------------
    # Main runner
    # ------------------------------------------------------------------

    def run(
        self,
        file_path: str | Path,
        strategy_transform=None,
    ) -> Dict[str, Any]:

        file_path = Path(
            file_path
        )

        print()
        print("=" * 80)
        print("PAPER TRADING RUNNER")
        print("=" * 80)

        print()

        print(
            f"Market data: {file_path}"
        )

        print(
            f"Strategy: {self.strategy_name}"
        )

        print(
            f"Initial balance: "
            f"{self.initial_balance:,.2f}"
        )

        # --------------------------------------------------------------
        # 1. Market analysis
        # --------------------------------------------------------------

        print()
        print(
            "[1/4] Running market analysis pipeline..."
        )

        pipeline_report = self.pipeline.run(
            str(file_path)
        )

        if not isinstance(
            pipeline_report,
            dict,
        ):
            raise TypeError(
                "TradingPipeline.run() must return a dictionary."
            )

        analyzed_data = pipeline_report.get(
            "data"
        )

        if analyzed_data is None:
            raise KeyError(
                "Pipeline report does not contain analyzed 'data'."
            )

        print(
            f"PASS: pipeline analyzed "
            f"{len(analyzed_data):,} rows"
        )

        # --------------------------------------------------------------
        # 2. Start persistent session
        # --------------------------------------------------------------

        print()
        print(
            "[2/4] Starting persistent paper session..."
        )

        session_id = self.session.start(
            self.initial_balance
        )

        print(
            f"PASS: session started "
            f"{session_id}"
        )

        # --------------------------------------------------------------
        # 3. Run actual paper engine
        # --------------------------------------------------------------

        print()
        print(
            "[3/4] Running paper trading simulation..."
        )

        paper_report = self.paper_engine.run(
            analyzed_data,
            strategy_name=self.strategy_name,
            strategy_transform=strategy_transform,
        )

        if not isinstance(
            paper_report,
            dict,
        ):
            raise TypeError(
                "PaperTradingEngine.run() must return a dictionary."
            )

        if paper_report.get("mode") != "PAPER":
            raise AssertionError(
                "Paper engine did not return PAPER mode."
            )

        if paper_report.get("live_trading") is not False:
            raise AssertionError(
                "Paper report is not explicitly marked "
                "live_trading=False."
            )

        print(
            "PASS: paper trading simulation completed"
        )

        # --------------------------------------------------------------
        # 4. Persistence + evaluation
        # --------------------------------------------------------------

        print()
        print(
            "[4/4] Persisting report, monitoring, "
            "and evaluating session..."
        )

        processed = self.session.process_report(
            paper_report
        )

        if not isinstance(
            processed,
            dict,
        ):
            raise TypeError(
                "PaperTradingSession.process_report() "
                "must return a dictionary."
            )

        paper_evaluation = (
            self.paper_evaluator.evaluate(
                paper_report
            )
        )

        unified_health = (
            self._build_unified_health(
                pipeline_report=pipeline_report,
                paper_report=paper_report,
                paper_evaluation=paper_evaluation,
            )
        )

        print(
            "PASS: report persisted "
            "and session processed"
        )

        print(
            "PASS: paper session "
            "evaluation generated"
        )

        # --------------------------------------------------------------
        # Finish the persistent session.
        # --------------------------------------------------------------

        self.session.finish()

        print(
            "PASS: paper session finished"
        )

        # Refresh the session AFTER finish().
        finished_session = self.session.get_session()

        # Refresh persisted counts AFTER all writes are complete.
        record_counts = self.session.get_record_counts()

        self._print_summary(
            paper_report=paper_report,
            paper_evaluation=paper_evaluation,
            unified_health=unified_health,
            record_counts=record_counts,
        )

        return {
            "status": "COMPLETE",
            "strategy_name": self.strategy_name,
            "market_data_file": str(file_path),
            "pipeline": pipeline_report,
            "data": analyzed_data,
            "paper_report": paper_report,
            "paper_evaluation": paper_evaluation,
            "unified_health": unified_health,

            # Compatibility alias used by earlier code.
            "evaluation": paper_evaluation,

            "session_id": session_id,
            "session": finished_session,
            "monitor": processed.get(
                "monitor"
            ),
            "record_counts": record_counts,
        }


def run_paper_trading(
    file_path: str | Path,
    initial_balance: float = 10_000.0,
    strategy_name: str = "XAUUSD_PAPER_TEST",
    **kwargs,
) -> Dict[str, Any]:

    runner = PaperTradingRunner(
        initial_balance=initial_balance,
        strategy_name=strategy_name,
        **kwargs,
    )

    return runner.run(
        file_path
    )


if __name__ == "__main__":

    default_file = Path(
        "data",
        "xauusd",
        "raw",
        "XAUUSD_5m.csv",
    )

    result = run_paper_trading(
        default_file
    )

    print()

    print(
        f"Runner status: "
        f"{result.get('status')}"
    )

    unified_status = PaperTradingRunner._status(
        result.get("unified_health")
    )

    print(
        f"Unified strategy health: "
        f"{unified_status}"
    )