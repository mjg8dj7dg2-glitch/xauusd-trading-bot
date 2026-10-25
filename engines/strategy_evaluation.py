from typing import Any, Dict


class StrategyEvaluationEngine:
    """
    Combines existing strategy-analysis results into one
    auditable evaluation report.

    This engine does NOT:
        - modify strategy rules
        - create trades
        - execute trades
        - automatically promote a strategy
        - automatically change risk settings

    It combines evidence produced by other engines and passes
    robustness evidence through the StrategyLifecycleEngine.
    """

    def __init__(self, lifecycle_engine=None):
        if lifecycle_engine is None:
            from engines.strategy_lifecycle import (
                StrategyLifecycleEngine,
            )

            lifecycle_engine = StrategyLifecycleEngine()

        self.lifecycle_engine = lifecycle_engine

    @staticmethod
    def _number(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _integer(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_status(result):
        if not isinstance(result, dict):
            return "UNKNOWN"

        status = result.get("status")

        if status is None:
            return "UNKNOWN"

        return str(status).upper()

    @classmethod
    def _regime_status(cls, regime_report):
        """
        Return the most important regime status.

        PAUSED takes priority over REVIEW, which takes priority
        over ordinary ACTIVE/healthy regimes.
        """
        if not isinstance(regime_report, dict):
            return "NOT_PROVIDED"

        statuses = []

        for value in regime_report.values():
            if isinstance(value, dict):
                status = value.get("status")
                if status is not None:
                    statuses.append(str(status).upper())

        if "PAUSED" in statuses:
            return "PAUSED"

        if "REVIEW" in statuses:
            return "REVIEW"

        if statuses and all(
            status in {"ACTIVE", "STABLE", "HEALTHY"}
            for status in statuses
        ):
            return "ACTIVE"

        if statuses:
            return statuses[0]

        return "NOT_PROVIDED"

    @classmethod
    def _paper_evaluation_status(cls, paper_evaluation):
        if not isinstance(paper_evaluation, dict):
            return "NOT_PROVIDED"

        return cls._get_status(paper_evaluation)

    @classmethod
    def _calculate_overall_status(
        cls,
        lifecycle,
        health_status,
        regime_report,
        paper_state,
        paper_evaluation,
        robustness_result,
    ):
        """
        Calculate the unified strategy-health status.

        Priority:
            1. PAUSED safety/health conditions
            2. REVIEW conditions
            3. insufficient evidence
            4. lifecycle decision
            5. ACTIVE
            6. lifecycle fallback
        """

        lifecycle_status = cls._get_status(lifecycle)

        supplied_health = (
            str(health_status).upper()
            if health_status is not None
            else "NOT_PROVIDED"
        )

        regime_status = cls._regime_status(regime_report)

        paper_eval_status = cls._paper_evaluation_status(
            paper_evaluation
        )

        paper_complete = bool(
            paper_state.get(
                "complete",
                False,
            )
        )

        robustness_status = cls._get_status(
            robustness_result
        )

        # --------------------------------------------------
        # PAUSED has the highest priority.
        # --------------------------------------------------

        if supplied_health == "PAUSED":
            return "PAUSED"

        if regime_status == "PAUSED":
            return "PAUSED"

        if lifecycle_status == "PAUSED":
            return "PAUSED"

        # --------------------------------------------------
        # REVIEW conditions.
        # --------------------------------------------------

        if supplied_health == "REVIEW":
            return "REVIEW"

        if regime_status == "REVIEW":
            return "REVIEW"

        if paper_eval_status == "REVIEW":
            return "REVIEW"

        if paper_state.get("state") == "REVIEW":
            return "REVIEW"

        # --------------------------------------------------
        # Insufficient evidence.
        # --------------------------------------------------

        if (
            supplied_health == "INSUFFICIENT_DATA"
            and not paper_complete
        ):
            return "INSUFFICIENT_DATA"

        if robustness_status in {
            "INSUFFICIENT_DATA",
            "INSUFFICIENT",
        }:
            return "INSUFFICIENT_DATA"

        # --------------------------------------------------
        # Lifecycle engine is the main evidence gate.
        # --------------------------------------------------

        if lifecycle_status in {
            "VALIDATION",
            "PAPER_TEST",
            "ACTIVE",
            "REVIEW",
            "PAUSED",
            "INSUFFICIENT_DATA",
        }:
            return lifecycle_status

        # --------------------------------------------------
        # Explicit healthy paper observation can support ACTIVE.
        # --------------------------------------------------

        paper_healthy = bool(
            paper_state.get(
                "healthy",
                False,
            )
        )

        if (
            paper_complete
            and paper_healthy
            and paper_eval_status in {
                "STABLE",
                "STABLE_OBSERVATION",
                "ACTIVE",
                "HEALTHY",
                "COMPLETE",
            }
            and supplied_health in {
                "ACTIVE",
                "NOT_PROVIDED",
            }
        ):
            return "ACTIVE"

        # --------------------------------------------------
        # Final conservative fallback.
        # --------------------------------------------------

        return lifecycle_status or "UNKNOWN"

    def evaluate_variant(
        self,
        variant_name: str,
        robustness_result: Dict[str, Any],
        paper_state: Dict[str, Any] | None = None,
        currently_active: bool = False,
        health_status: str | None = None,
        regime_report: Dict[str, Any] | None = None,
        strategy_health_report: Dict[str, Any] | None = None,
        memory_report: Dict[str, Any] | None = None,
        paper_evaluation: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Evaluate one strategy version from existing evidence.
        """

        paper_state = paper_state or {}

        regime_report = regime_report or {}

        paper_complete = bool(
            paper_state.get(
                "complete",
                False,
            )
        )

        paper_healthy = bool(
            paper_state.get(
                "healthy",
                False,
            )
        )

        lifecycle = self.lifecycle_engine.determine_state(
            robustness_result=robustness_result,
            paper_trading_complete=paper_complete,
            paper_trading_healthy=paper_healthy,
            currently_active=currently_active,
            health_status=health_status,
        )

        robustness_status = self._get_status(
            robustness_result
        )

        overall_status = self._calculate_overall_status(
            lifecycle=lifecycle,
            health_status=health_status,
            regime_report=regime_report,
            paper_state=paper_state,
            paper_evaluation=paper_evaluation,
            robustness_result=robustness_result,
        )

        result = {
            "variant_name": variant_name,

            # --------------------------------------------------
            # New unified health section.
            # --------------------------------------------------

            "overall": {
                "status": overall_status,
                "strategy": variant_name,
                "lifecycle_status": self._get_status(
                    lifecycle
                ),
                "robustness_status": robustness_status,
                "health_status": (
                    str(health_status).upper()
                    if health_status is not None
                    else "NOT_PROVIDED"
                ),
                "regime_status": self._regime_status(
                    regime_report
                ),
                "paper_evaluation_status": (
                    self._paper_evaluation_status(
                        paper_evaluation
                    )
                ),
            },

            # --------------------------------------------------
            # Preserve top-level status for older callers.
            # --------------------------------------------------

            "status": overall_status,

            "robustness": {
                "status": robustness_status,

                "validation_trades": self._integer(
                    robustness_result.get(
                        "validation_trades"
                    )
                ),

                "validation_windows": self._integer(
                    robustness_result.get(
                        "windows_with_trades"
                    )
                ),

                "average_pf": self._number(
                    robustness_result.get(
                        "average_window_profit_factor"
                    )
                ),

                "positive_window_ratio": self._number(
                    robustness_result.get(
                        "positive_window_ratio"
                    )
                ),

                "total_validation_pnl": self._number(
                    robustness_result.get(
                        "total_validation_pnl"
                    )
                ),

                "maximum_drawdown": self._number(
                    robustness_result.get(
                        "maximum_window_drawdown"
                    )
                ),
            },

            "lifecycle": lifecycle,

            "paper_trading": {
                "complete": paper_complete,

                "healthy": paper_healthy,

                "state": paper_state.get(
                    "state",
                    "NOT_STARTED",
                ),

                "trades": self._integer(
                    paper_state.get(
                        "trades"
                    )
                ),

                "evaluation": paper_evaluation,
            },

            "health": {
                "status": (
                    str(health_status).upper()
                    if health_status is not None
                    else "NOT_PROVIDED"
                ),

                "report": strategy_health_report,
            },

            "regime_analysis": regime_report,

            "trade_memory": memory_report,
        }

        return result

    def evaluate_all(
        self,
        robustness_report: Dict[str, Any],
        paper_states: Dict[str, Dict[str, Any]] | None = None,
        active_strategies: Dict[str, bool] | None = None,
        health_states: Dict[str, str] | None = None,
        regime_reports: Dict[str, Dict[str, Any]] | None = None,
        strategy_health_reports: Dict[str, Dict[str, Any]] | None = None,
        memory_reports: Dict[str, Dict[str, Any]] | None = None,
        paper_evaluations: Dict[str, Dict[str, Any]] | None = None,
        currently_active: Dict[str, bool] | None = None,
    ) -> Dict[str, Any]:
        """
        Combine all available strategy evidence.

        Compatibility:
        - active_strategies is the original parameter.
        - currently_active is accepted as a newer alias.
        - paper_evaluations is additional paper-session evidence.
        """

        paper_states = paper_states or {}

        active_strategies = active_strategies or {}

        if currently_active:
            active_strategies = {
                **active_strategies,
                **currently_active,
            }

        health_states = health_states or {}

        regime_reports = regime_reports or {}

        strategy_health_reports = (
            strategy_health_reports or {}
        )

        memory_reports = memory_reports or {}

        paper_evaluations = paper_evaluations or {}

        variants = robustness_report.get(
            "variants",
            {},
        )

        results = {}

        for variant_name, robustness_result in variants.items():

            results[variant_name] = self.evaluate_variant(
                variant_name=variant_name,

                robustness_result=robustness_result,

                paper_state=paper_states.get(
                    variant_name,
                    {},
                ),

                currently_active=bool(
                    active_strategies.get(
                        variant_name,
                        False,
                    )
                ),

                health_status=health_states.get(
                    variant_name
                ),

                regime_report=regime_reports.get(
                    variant_name
                ),

                strategy_health_report=(
                    strategy_health_reports.get(
                        variant_name
                    )
                ),

                memory_report=memory_reports.get(
                    variant_name
                ),

                paper_evaluation=(
                    paper_evaluations.get(
                        variant_name
                    )
                ),
            )

        status_counts = {}

        for result in results.values():
            status = result.get(
                "overall",
                {},
            ).get(
                "status",
                "UNKNOWN",
            )

            status_counts[status] = (
                status_counts.get(
                    status,
                    0,
                )
                + 1
            )

        return {
            "status": "COMPLETE",

            "strategy_count": len(results),

            "strategies": results,

            "status_counts": status_counts,
        }

    @staticmethod
    def build_dashboard_summary(
        report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a compact dashboard-friendly summary.

        This is analysis/reporting only. It does not authorize
        live trading or change strategy state.
        """

        strategies = report.get(
            "strategies",
            {},
        )

        summary = {
            "strategy_count": len(strategies),
            "active": 0,
            "review": 0,
            "paused": 0,
            "validation": 0,
            "paper_test": 0,
            "insufficient_data": 0,
            "unknown": 0,
        }

        for result in strategies.values():

            overall = result.get(
                "overall",
                {},
            )

            status = str(
                overall.get(
                    "status",
                    result.get(
                        "status",
                        "UNKNOWN",
                    ),
                )
            ).upper()

            if status == "ACTIVE":
                summary["active"] += 1

            elif status == "REVIEW":
                summary["review"] += 1

            elif status == "PAUSED":
                summary["paused"] += 1

            elif status == "VALIDATION":
                summary["validation"] += 1

            elif status == "PAPER_TEST":
                summary["paper_test"] += 1

            elif status == "INSUFFICIENT_DATA":
                summary["insufficient_data"] += 1

            else:
                summary["unknown"] += 1

        return summary

    @staticmethod
    def print_report(
        report: Dict[str, Any]
    ) -> None:
        print("=" * 80)
        print("STRATEGY EVALUATION REPORT")
        print("=" * 80)

        print(
            f"Status: "
            f"{report.get('status', 'UNKNOWN')}"
        )

        print(
            f"Strategies: "
            f"{report.get('strategy_count', 0)}"
        )

        status_counts = report.get(
            "status_counts",
            {},
        )

        if status_counts:
            print(
                f"Status counts: "
                f"{status_counts}"
            )

        strategies = report.get(
            "strategies",
            {},
        )

        for name, result in strategies.items():
            print()
            print("-" * 80)
            print(f"Strategy: {name}")
            print("-" * 80)

            overall = result.get(
                "overall",
                {},
            )

            robustness = result.get(
                "robustness",
                {},
            )

            paper = result.get(
                "paper_trading",
                {},
            )

            health = result.get(
                "health",
                {},
            )

            lifecycle = result.get(
                "lifecycle",
                {},
            )

            print(
                f"Overall: "
                f"{overall.get('status', 'UNKNOWN')}"
            )

            print(
                f"Robustness: "
                f"{robustness.get('status', 'UNKNOWN')}"
            )

            print(
                f"Lifecycle: "
                f"{lifecycle}"
            )

            print(
                f"Paper state: "
                f"{paper.get('state', 'NOT_STARTED')}"
            )

            print(
                f"Paper complete: "
                f"{paper.get('complete', False)}"
            )

            print(
                f"Paper healthy: "
                f"{paper.get('healthy', False)}"
            )

            print(
                f"Health: "
                f"{health.get('status', 'NOT_PROVIDED')}"
            )

            print(
                f"Regime: "
                f"{overall.get('regime_status', 'NOT_PROVIDED')}"
            )

            print(
                f"Paper evaluation: "
                f"{overall.get('paper_evaluation_status', 'NOT_PROVIDED')}"
            )