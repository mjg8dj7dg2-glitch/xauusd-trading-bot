from __future__ import annotations

from typing import Any, Dict, List


class StrategyRobustnessEngine:
    """
    Evaluates walk-forward out-of-sample results for strategy robustness.

    This engine does not modify strategies or execute trades.
    It only evaluates the evidence produced by walk-forward testing.
    """

    def __init__(
        self,
        minimum_total_validation_trades: int = 30,
        minimum_windows: int = 4,
        minimum_windows_with_trades: int = 3,
        minimum_profit_factor: float = 1.05,
        robust_profit_factor: float = 1.15,
        minimum_positive_windows_ratio: float = 0.50,
        robust_positive_windows_ratio: float = 0.75,
        maximum_drawdown_for_robust: float = 0.10,
    ):
        self.minimum_total_validation_trades = (
            minimum_total_validation_trades
        )
        self.minimum_windows = minimum_windows
        self.minimum_windows_with_trades = minimum_windows_with_trades
        self.minimum_profit_factor = minimum_profit_factor
        self.robust_profit_factor = robust_profit_factor
        self.minimum_positive_windows_ratio = minimum_positive_windows_ratio
        self.robust_positive_windows_ratio = robust_positive_windows_ratio
        self.maximum_drawdown_for_robust = maximum_drawdown_for_robust

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _is_positive_profit_factor(value: Any) -> bool:
        try:
            return float(value) > 1.0
        except (TypeError, ValueError):
            return False

    def _summarize_windows(
        self,
        variant_name: str,
        windows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_windows = len(windows)

        validation_windows = []
        validation_trades = 0
        positive_windows = 0
        profitable_windows = 0
        pf_above_one_windows = 0

        drawdowns = []
        profit_factors = []
        pnl_values = []

        for item in windows:
            variants = item.get("variants", {})

            if variant_name not in variants:
                continue

            variant_data = variants[variant_name]
            validation = variant_data.get("validation", {})

            trades = self._safe_int(validation.get("trades"))

            if trades <= 0:
                continue

            validation_windows.append(item)

            validation_trades += trades

            pnl = self._safe_float(validation.get("total_pnl"))
            pf = self._safe_float(validation.get("profit_factor"))

            drawdown = self._safe_float(
                validation.get("max_drawdown")
            )

            pnl_values.append(pnl)
            profit_factors.append(pf)
            drawdowns.append(drawdown)

            if pnl > 0:
                positive_windows += 1

            if pnl > 0:
                profitable_windows += 1

            if self._is_positive_profit_factor(pf):
                pf_above_one_windows += 1

        windows_with_trades = len(validation_windows)

        if windows_with_trades > 0:
            positive_window_ratio = (
                positive_windows / windows_with_trades
            )
        else:
            positive_window_ratio = 0.0

        if profit_factors:
            average_pf = sum(profit_factors) / len(profit_factors)
        else:
            average_pf = 0.0

        if pnl_values:
            total_pnl = sum(pnl_values)
        else:
            total_pnl = 0.0

        if drawdowns:
            maximum_window_drawdown = max(drawdowns)
            average_window_drawdown = (
                sum(drawdowns) / len(drawdowns)
            )
        else:
            maximum_window_drawdown = 0.0
            average_window_drawdown = 0.0

        if profit_factors:
            minimum_window_pf = min(profit_factors)
            maximum_window_pf = max(profit_factors)
        else:
            minimum_window_pf = 0.0
            maximum_window_pf = 0.0

        return {
            "variant": variant_name,
            "windows_total": total_windows,
            "windows_with_trades": windows_with_trades,
            "validation_trades": validation_trades,
            "positive_windows": positive_windows,
            "positive_window_ratio": positive_window_ratio,
            "pf_above_one_windows": pf_above_one_windows,
            "average_window_profit_factor": average_pf,
            "minimum_window_profit_factor": minimum_window_pf,
            "maximum_window_profit_factor": maximum_window_pf,
            "total_validation_pnl": total_pnl,
            "average_window_drawdown": average_window_drawdown,
            "maximum_window_drawdown": maximum_window_drawdown,
        }

    def _classify(
        self,
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        reasons: List[str] = []

        trades = summary["validation_trades"]
        windows_total = summary["windows_total"]
        windows_with_trades = summary["windows_with_trades"]
        positive_ratio = summary["positive_window_ratio"]
        average_pf = summary["average_window_profit_factor"]
        maximum_drawdown = summary["maximum_window_drawdown"]

        if windows_total < self.minimum_windows:
            reasons.append(
                f"Only {windows_total} walk-forward windows; "
                f"{self.minimum_windows} required."
            )

        if windows_with_trades < self.minimum_windows_with_trades:
            reasons.append(
                f"Only {windows_with_trades} validation windows "
                f"contained trades; "
                f"{self.minimum_windows_with_trades} required."
            )

        if trades < self.minimum_total_validation_trades:
            reasons.append(
                f"Only {trades} validation trades; "
                f"{self.minimum_total_validation_trades} required."
            )

        if average_pf < self.minimum_profit_factor:
            reasons.append(
                f"Average validation-window PF "
                f"{average_pf:.4f} is below "
                f"{self.minimum_profit_factor:.2f}."
            )

        if positive_ratio < self.minimum_positive_windows_ratio:
            reasons.append(
                f"Only {positive_ratio:.1%} of validation windows "
                f"were profitable; "
                f"{self.minimum_positive_windows_ratio:.1%} required."
            )

        if reasons:
            return {
                "status": "REVIEW",
                "reasons": reasons,
            }

        robust_reasons = []

        if average_pf < self.robust_profit_factor:
            robust_reasons.append(
                f"Average validation-window PF "
                f"{average_pf:.4f} is below the "
                f"robust threshold of "
                f"{self.robust_profit_factor:.2f}."
            )

        if positive_ratio < self.robust_positive_windows_ratio:
            robust_reasons.append(
                f"Only {positive_ratio:.1%} of validation windows "
                f"were profitable; "
                f"{self.robust_positive_windows_ratio:.1%} "
                f"is required for ROBUST."
            )

        if maximum_drawdown > self.maximum_drawdown_for_robust:
            robust_reasons.append(
                f"Maximum validation-window drawdown "
                f"{maximum_drawdown:.2%} exceeds the "
                f"robust threshold of "
                f"{self.maximum_drawdown_for_robust:.2%}."
            )

        if robust_reasons:
            return {
                "status": "REVIEW",
                "reasons": robust_reasons,
            }

        return {
            "status": "ROBUST",
            "reasons": [
                "Sufficient validation data across multiple "
                "walk-forward windows.",
                "Validation-window profitability is consistent.",
                "Validation-window profit factor meets the "
                "robust threshold.",
                "Maximum validation-window drawdown is within "
                "the configured robustness threshold.",
            ],
        }

    def analyze(
        self,
        walk_forward_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze all strategy variants in a WalkForwardEngine result.
        """

        windows = walk_forward_results.get("windows", [])

        if not windows:
            return {
                "status": "INSUFFICIENT_DATA",
                "variants": {},
                "message": "No walk-forward windows were supplied.",
            }

        variant_names = set()

        for window in windows:
            variants = window.get("variants", {})
            variant_names.update(variants.keys())

        results: Dict[str, Any] = {}

        for variant_name in sorted(variant_names):
            summary = self._summarize_windows(
                variant_name,
                windows,
            )

            classification = self._classify(summary)

            results[variant_name] = {
                **summary,
                **classification,
            }

        return {
            "status": "COMPLETE",
            "windows_total": len(windows),
            "variants": results,
        }

    def compare_to_baseline(
        self,
        robustness_report: Dict[str, Any],
        baseline_name: str = "V1_BASELINE",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare each variant's robustness metrics against the baseline.
        """

        variants = robustness_report.get("variants", {})

        if baseline_name not in variants:
            return {}

        baseline = variants[baseline_name]

        comparisons: Dict[str, Dict[str, Any]] = {}

        for variant_name, variant in variants.items():
            if variant_name == baseline_name:
                continue

            comparisons[variant_name] = {
                "validation_trade_change": (
                    variant["validation_trades"]
                    - baseline["validation_trades"]
                ),
                "positive_window_ratio_change": (
                    variant["positive_window_ratio"]
                    - baseline["positive_window_ratio"]
                ),
                "average_pf_change": (
                    variant["average_window_profit_factor"]
                    - baseline["average_window_profit_factor"]
                ),
                "total_pnl_change": (
                    variant["total_validation_pnl"]
                    - baseline["total_validation_pnl"]
                ),
                "maximum_drawdown_change": (
                    variant["maximum_window_drawdown"]
                    - baseline["maximum_window_drawdown"]
                ),
            }

        return comparisons

    def build_report(
        self,
        walk_forward_results: Dict[str, Any],
        baseline_name: str = "V1_BASELINE",
    ) -> Dict[str, Any]:
        """
        Build a complete robustness report.
        """

        robustness = self.analyze(walk_forward_results)

        comparisons = self.compare_to_baseline(
            robustness,
            baseline_name=baseline_name,
        )

        robustness["baseline"] = baseline_name
        robustness["comparisons_to_baseline"] = comparisons

        return robustness

    @staticmethod
    def print_report(report: Dict[str, Any]) -> None:
        print()
        print("=" * 80)
        print("STRATEGY ROBUSTNESS REPORT")
        print("=" * 80)

        if report.get("status") != "COMPLETE":
            print(report.get("message", "No robustness results."))
            return

        print(
            f"Walk-forward windows: "
            f"{report.get('windows_total', 0)}"
        )

        variants = report.get("variants", {})

        for variant_name, result in variants.items():
            print()
            print("-" * 80)
            print(f"VARIANT: {variant_name}")
            print("-" * 80)

            print(f"Status: {result['status']}")
            print(
                f"Validation trades: "
                f"{result['validation_trades']}"
            )
            print(
                f"Windows with trades: "
                f"{result['windows_with_trades']}/"
                f"{result['windows_total']}"
            )
            print(
                f"Positive windows: "
                f"{result['positive_windows']}"
            )
            print(
                f"Positive-window ratio: "
                f"{result['positive_window_ratio']:.2%}"
            )
            print(
                f"Average window PF: "
                f"{result['average_window_profit_factor']:.4f}"
            )
            print(
                f"Minimum window PF: "
                f"{result['minimum_window_profit_factor']:.4f}"
            )
            print(
                f"Maximum window PF: "
                f"{result['maximum_window_profit_factor']:.4f}"
            )
            print(
                f"Total validation P&L: "
                f"{result['total_validation_pnl']:.2f}"
            )
            print(
                f"Maximum window drawdown: "
                f"{result['maximum_window_drawdown']:.2%}"
            )

            print("Reasons:")

            for reason in result.get("reasons", []):
                print(f" - {reason}")

        comparisons = report.get(
            "comparisons_to_baseline",
            {},
        )

        if comparisons:
            print()
            print("=" * 80)
            print("COMPARISON TO BASELINE")
            print("=" * 80)

            for variant_name, comparison in comparisons.items():
                print()
                print(variant_name)
                print(
                    "  Validation trades change: "
                    f"{comparison['validation_trade_change']:+d}"
                )
                print(
                    "  Positive-window ratio change: "
                    f"{comparison['positive_window_ratio_change']:+.2%}"
                )
                print(
                    "  Average PF change: "
                    f"{comparison['average_pf_change']:+.4f}"
                )
                print(
                    "  Validation P&L change: "
                    f"{comparison['total_pnl_change']:+.2f}"
                )
                print(
                    "  Maximum drawdown change: "
                    f"{comparison['maximum_drawdown_change']:+.2%}"
                )

        print()
        print("=" * 80)