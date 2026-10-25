from __future__ import annotations

from typing import Any, Dict


class StrategyLifecycleEngine:
    """
    Controls the research lifecycle of strategy versions.

    Possible states:

        EXPERIMENTAL
        VALIDATION
        PAPER_TEST
        ACTIVE
        REVIEW
        PAUSED

    This engine does not execute trades and does not modify strategies.
    """

    def __init__(
        self,
        minimum_validation_trades: int = 30,
        minimum_validation_windows: int = 4,
        minimum_average_pf: float = 1.05,
        minimum_positive_window_ratio: float = 0.50,
        robust_pf: float = 1.15,
        robust_positive_window_ratio: float = 0.75,
        maximum_drawdown: float = 0.10,
    ):
        self.minimum_validation_trades = minimum_validation_trades
        self.minimum_validation_windows = minimum_validation_windows
        self.minimum_average_pf = minimum_average_pf
        self.minimum_positive_window_ratio = (
            minimum_positive_window_ratio
        )

        self.robust_pf = robust_pf
        self.robust_positive_window_ratio = (
            robust_positive_window_ratio
        )
        self.maximum_drawdown = maximum_drawdown

    @staticmethod
    def _number(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _integer(
        value: Any,
        default: int = 0,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def evaluate_robustness(
        self,
        robustness_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert one strategy's robustness result into lifecycle evidence.
        """

        trades = self._integer(
            robustness_result.get("validation_trades")
        )

        windows = self._integer(
            robustness_result.get("windows_with_trades")
        )

        average_pf = self._number(
            robustness_result.get(
                "average_window_profit_factor"
            )
        )

        positive_ratio = self._number(
            robustness_result.get(
                "positive_window_ratio"
            )
        )

        maximum_drawdown = self._number(
            robustness_result.get(
                "maximum_window_drawdown"
            )
        )

        evidence = {
            "validation_trades": trades,
            "validation_windows": windows,
            "average_pf": average_pf,
            "positive_window_ratio": positive_ratio,
            "maximum_drawdown": maximum_drawdown,
            "minimum_trade_requirement_met": (
                trades >= self.minimum_validation_trades
            ),
            "minimum_window_requirement_met": (
                windows >= self.minimum_validation_windows
            ),
            "minimum_pf_requirement_met": (
                average_pf >= self.minimum_average_pf
            ),
            "minimum_positive_window_requirement_met": (
                positive_ratio
                >= self.minimum_positive_window_ratio
            ),
            "robust_pf_requirement_met": (
                average_pf >= self.robust_pf
            ),
            "robust_positive_window_requirement_met": (
                positive_ratio
                >= self.robust_positive_window_ratio
            ),
            "drawdown_requirement_met": (
                maximum_drawdown <= self.maximum_drawdown
            ),
        }

        return evidence

    def determine_state(
        self,
        robustness_result: Dict[str, Any],
        paper_trading_complete: bool = False,
        paper_trading_healthy: bool = False,
        currently_active: bool = False,
        health_status: str | None = None,
    ) -> Dict[str, Any]:
        """
        Determine the lifecycle state from available evidence.
        """

        evidence = self.evaluate_robustness(
            robustness_result
        )

        reasons = []

        if health_status is not None:
            normalized_health = str(
                health_status
            ).upper()
        else:
            normalized_health = ""

        # --------------------------------------------------------
        # Existing active strategies can be moved into REVIEW or
        # PAUSED if their health deteriorates.
        # --------------------------------------------------------

        if currently_active:
            if normalized_health == "PAUSED":
                return {
                    "state": "PAUSED",
                    "evidence": evidence,
                    "reasons": [
                        "Existing strategy health status is PAUSED."
                    ],
                }

            if normalized_health == "REVIEW":
                return {
                    "state": "REVIEW",
                    "evidence": evidence,
                    "reasons": [
                        "Existing strategy health status "
                        "requires review."
                    ],
                }

            return {
                "state": "ACTIVE",
                "evidence": evidence,
                "reasons": [
                    "Strategy is already active and no "
                    "new health warning was supplied."
                ],
            }

        # --------------------------------------------------------
        # Basic validation requirements.
        # --------------------------------------------------------

        if not evidence[
            "minimum_trade_requirement_met"
        ]:
            reasons.append(
                "Not enough validation trades."
            )

        if not evidence[
            "minimum_window_requirement_met"
        ]:
            reasons.append(
                "Not enough walk-forward validation windows."
            )

        if not evidence[
            "minimum_pf_requirement_met"
        ]:
            reasons.append(
                "Average validation PF is below "
                "the minimum threshold."
            )

        if not evidence[
            "minimum_positive_window_requirement_met"
        ]:
            reasons.append(
                "Too few validation windows were profitable."
            )

        # If the minimum evidence is not available, remain in
        # validation rather than pretending there is enough data.
        if reasons:
            return {
                "state": "VALIDATION",
                "evidence": evidence,
                "reasons": reasons,
            }

        # --------------------------------------------------------
        # Robustness has been demonstrated, but paper testing has
        # not yet been completed.
        # --------------------------------------------------------

        if not paper_trading_complete:
            return {
                "state": "PAPER_TEST",
                "evidence": evidence,
                "reasons": [
                    "Minimum validation requirements are met.",
                    "Paper trading has not yet been completed.",
                ],
            }

        # --------------------------------------------------------
        # Paper trading exists but did not remain healthy.
        # --------------------------------------------------------

        if not paper_trading_healthy:
            return {
                "state": "REVIEW",
                "evidence": evidence,
                "reasons": [
                    "Paper trading was completed, "
                    "but paper-trading health requirements "
                    "were not met."
                ],
            }

        # --------------------------------------------------------
        # Strong robustness + completed healthy paper test.
        # --------------------------------------------------------

        robust_requirements = [
            evidence[
                "robust_pf_requirement_met"
            ],
            evidence[
                "robust_positive_window_requirement_met"
            ],
            evidence[
                "drawdown_requirement_met"
            ],
        ]

        if all(robust_requirements):
            return {
                "state": "ACTIVE",
                "evidence": evidence,
                "reasons": [
                    "Validation evidence meets the "
                    "robustness thresholds.",
                    "Paper trading was completed.",
                    "Paper-trading health requirements "
                    "were met."
                ],
            }

        return {
            "state": "REVIEW",
            "evidence": evidence,
            "reasons": [
                "Minimum validation requirements are met, "
                "but the stronger robustness requirements "
                "were not all met."
            ],
        }

    def evaluate_all(
        self,
        robustness_report: Dict[str, Any],
        paper_states: Dict[str, Dict[str, Any]] | None = None,
        active_strategies: Dict[str, bool] | None = None,
        health_states: Dict[str, str] | None = None,
    ) -> Dict[str, Any]:
        """
        Evaluate every strategy variant in a robustness report.
        """

        paper_states = paper_states or {}
        active_strategies = active_strategies or {}
        health_states = health_states or {}

        variants = robustness_report.get(
            "variants",
            {}
        )

        results = {}

        for variant_name, robustness_result in variants.items():

            paper_info = paper_states.get(
                variant_name,
                {}
            )

            paper_complete = bool(
                paper_info.get(
                    "complete",
                    False
                )
            )

            paper_healthy = bool(
                paper_info.get(
                    "healthy",
                    False
                )
            )

            currently_active = bool(
                active_strategies.get(
                    variant_name,
                    False
                )
            )

            health_status = health_states.get(
                variant_name
            )

            results[variant_name] = self.determine_state(
                robustness_result=robustness_result,
                paper_trading_complete=paper_complete,
                paper_trading_healthy=paper_healthy,
                currently_active=currently_active,
                health_status=health_status,
            )

        return {
            "status": "COMPLETE",
            "strategies": results,
        }

    @staticmethod
    def print_report(
        report: Dict[str, Any]
    ) -> None:

        print()
        print("=" * 80)
        print("STRATEGY LIFECYCLE REPORT")
        print("=" * 80)

        if report.get("status") != "COMPLETE":
            print("No lifecycle results available.")
            return

        strategies = report.get(
            "strategies",
            {}
        )

        for name, result in strategies.items():

            evidence = result.get(
                "evidence",
                {}
            )

            print()
            print("-" * 80)
            print(f"STRATEGY: {name}")
            print("-" * 80)

            print(
                f"Lifecycle state: "
                f"{result['state']}"
            )

            print(
                f"Validation trades: "
                f"{evidence.get('validation_trades', 0)}"
            )

            print(
                f"Validation windows: "
                f"{evidence.get('validation_windows', 0)}"
            )

            print(
                f"Average PF: "
                f"{evidence.get('average_pf', 0.0):.4f}"
            )

            print(
                f"Positive-window ratio: "
                f"{evidence.get('positive_window_ratio', 0.0):.2%}"
            )

            print(
                f"Maximum drawdown: "
                f"{evidence.get('maximum_drawdown', 0.0):.2%}"
            )

            print("Reasons:")

            for reason in result.get(
                "reasons",
                []
            ):
                print(f" - {reason}")

        print()
        print("=" * 80)