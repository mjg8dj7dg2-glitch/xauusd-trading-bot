"""
Walk-forward testing engine for the local XAUUSD strategy project.

Purpose
-------
Evaluate the existing V1-V6 strategy variants across multiple chronological
development/validation windows.

This module does NOT change strategy rules. It repeatedly evaluates the same
variants on earlier development data and then on the immediately following
unseen validation data.

The validation windows are chronological and non-overlapping by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from engines.strategy_experiment import StrategyExperiment


@dataclass
class WalkForwardWindow:
    index: int
    development_start: pd.Timestamp
    development_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp


class WalkForwardEngine:
    """Run chronological walk-forward validation for strategy variants."""

    def __init__(
        self,
        experiment: StrategyExperiment | None = None,
        development_days: int = 70,
        validation_days: int = 28,
        step_days: int = 28,
        minimum_validation_trades: int = 5,
    ):
        if development_days <= 0:
            raise ValueError("development_days must be greater than zero.")

        if validation_days <= 0:
            raise ValueError("validation_days must be greater than zero.")

        if step_days <= 0:
            raise ValueError("step_days must be greater than zero.")

        if minimum_validation_trades < 0:
            raise ValueError(
                "minimum_validation_trades cannot be negative."
            )

        self.experiment = experiment or StrategyExperiment()
        self.development_days = int(development_days)
        self.validation_days = int(validation_days)
        self.step_days = int(step_days)
        self.minimum_validation_trades = int(
            minimum_validation_trades
        )

    @staticmethod
    def _prepare_timestamp_column(df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        if "timestamp" not in result.columns:
            raise ValueError(
                "Walk-forward data must contain a 'timestamp' column."
            )

        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            utc=True,
            errors="coerce",
        )

        result = result.dropna(subset=["timestamp"])
        result = result.sort_values("timestamp")
        result = result.drop_duplicates(
            subset=["timestamp"],
            keep="last",
        )
        result = result.reset_index(drop=True)

        if result.empty:
            raise ValueError(
                "No valid timestamped rows remain after cleaning."
            )

        return result

    def build_windows(
        self,
        analyzed_data: pd.DataFrame,
    ) -> List[WalkForwardWindow]:
        """Create chronological development/validation windows."""

        data = self._prepare_timestamp_column(analyzed_data)

        start = data["timestamp"].min()
        end = data["timestamp"].max()

        development_delta = pd.Timedelta(
            days=self.development_days
        )
        validation_delta = pd.Timedelta(
            days=self.validation_days
        )
        step_delta = pd.Timedelta(
            days=self.step_days
        )

        windows: List[WalkForwardWindow] = []

        validation_start = start + development_delta
        index = 1

        while validation_start + validation_delta <= end:
            development_start = validation_start - development_delta
            validation_end = validation_start + validation_delta

            windows.append(
                WalkForwardWindow(
                    index=index,
                    development_start=development_start,
                    development_end=validation_start,
                    validation_start=validation_start,
                    validation_end=validation_end,
                )
            )

            validation_start = validation_start + step_delta
            index += 1

        return windows

    @staticmethod
    def _slice(
        data: pd.DataFrame,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        mask = (
            (data["timestamp"] >= start)
            & (data["timestamp"] < end)
        )

        return data.loc[mask].copy().reset_index(drop=True)

    @staticmethod
    def _trade_time(trade: Dict, field: str) -> pd.Timestamp | None:
        value = trade.get(field)

        if value is None:
            return None

        try:
            return pd.to_datetime(value, utc=True)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _combine_trades(results: List[Dict]) -> List[Dict]:
        trades: List[Dict] = []

        for result in results:
            for trade in result.get("trades", []):
                trades.append(dict(trade))

        trades.sort(
            key=lambda trade: (
                WalkForwardEngine._trade_time(
                    trade,
                    "entry_time",
                )
                or pd.Timestamp.min.tz_localize("UTC")
            )
        )

        return trades

    @staticmethod
    def _aggregate_trade_results(
        results: List[Dict],
    ) -> Dict:
        trades = WalkForwardEngine._combine_trades(results)

        wins = sum(
            1
            for trade in trades
            if str(trade.get("result", "")).upper() == "WIN"
            or float(trade.get("pnl", 0.0)) > 0
        )

        losses = sum(
            1
            for trade in trades
            if float(trade.get("pnl", 0.0)) < 0
        )

        total_pnl = sum(
            float(trade.get("pnl", 0.0))
            for trade in trades
        )

        gross_profit = sum(
            float(trade.get("pnl", 0.0))
            for trade in trades
            if float(trade.get("pnl", 0.0)) > 0
        )

        gross_loss = sum(
            float(trade.get("pnl", 0.0))
            for trade in trades
            if float(trade.get("pnl", 0.0)) < 0
        )

        if gross_loss < 0:
            profit_factor = gross_profit / abs(gross_loss)
        elif gross_profit > 0:
            profit_factor = None
        else:
            profit_factor = 0.0

        trade_count = len(trades)

        if trade_count:
            win_rate = wins / trade_count
        else:
            win_rate = 0.0

        # Calculate drawdown from the chronological combined trade equity.
        starting_balance = float(
            getattr(
                results[0],
                "initial_balance",
                10000.0,
            )
        ) if results else 10000.0

        equity = starting_balance
        peak = equity
        max_drawdown = 0.0

        for trade in trades:
            equity += float(trade.get("pnl", 0.0))
            peak = max(peak, equity)

            if peak > 0:
                drawdown = (peak - equity) / peak
                max_drawdown = max(
                    max_drawdown,
                    drawdown,
                )

        return {
            "trades": trade_count,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "max_drawdown": max_drawdown,
            "sufficient_data": (
                trade_count >= 5
            ),
        }

    def run(
        self,
        analyzed_data: pd.DataFrame,
        variants=None,
    ) -> Dict:
        """
        Run all variants over all walk-forward windows.

        Returns a dictionary containing:
        - window definitions
        - per-variant/per-window results
        - aggregate validation results
        - baseline-relative validation changes
        """

        data = self._prepare_timestamp_column(analyzed_data)

        if variants is None:
            variants = self.experiment.get_standard_variants()

        windows = self.build_windows(data)

        if not windows:
            raise ValueError(
                "Not enough historical data to create a walk-forward window."
            )

        window_reports: List[Dict] = []

        for window in windows:
            development_data = self._slice(
                data,
                window.development_start,
                window.development_end,
            )

            validation_data = self._slice(
                data,
                window.validation_start,
                window.validation_end,
            )

            variant_reports: Dict[str, Dict] = {}

            for variant_name, transform in variants:
                development_result = (
                    self.experiment.run_variant(
                        analyzed_data=development_data,
                        variant_name=variant_name,
                        transform=transform,
                    )
                )

                validation_result = (
                    self.experiment.run_variant(
                        analyzed_data=validation_data,
                        variant_name=variant_name,
                        transform=transform,
                    )
                )

                development_summary = (
                    self.experiment.summarize_result(
                        development_result
                    )
                )

                validation_summary = (
                    self.experiment.summarize_result(
                        validation_result
                    )
                )

                variant_reports[variant_name] = {
                    "development": development_summary,
                    "validation": validation_summary,
                    "validation_result": validation_result,
                }

            window_reports.append(
                {
                    "window": window,
                    "development_rows": len(
                        development_data
                    ),
                    "validation_rows": len(
                        validation_data
                    ),
                    "variants": variant_reports,
                }
            )

        aggregate = {}

        for variant_name, _ in variants:
            validation_results = [
                report["variants"][variant_name][
                    "validation_result"
                ]
                for report in window_reports
            ]

            development_results = [
                self.experiment.run_variant(
                    analyzed_data=self._slice(
                        data,
                        report["window"].development_start,
                        report["window"].development_end,
                    ),
                    variant_name=variant_name,
                    transform=dict(variants)[variant_name],
                )
                for report in window_reports
            ]

            validation_summary = (
                self._aggregate_trade_results(
                    validation_results
                )
            )

            development_summary = (
                self._aggregate_trade_results(
                    development_results
                )
            )

            valid_windows = [
                report["variants"][variant_name][
                    "validation"
                ]
                for report in window_reports
                if report["variants"][variant_name][
                    "validation"
                ]["trades"]
                >= self.minimum_validation_trades
            ]

            positive_pf_windows = sum(
                1
                for summary in valid_windows
                if (
                    summary["profit_factor"] is not None
                    and summary["profit_factor"] > 1.0
                )
            )

            positive_pnl_windows = sum(
                1
                for summary in valid_windows
                if summary["total_pnl"] > 0
            )

            if valid_windows:
                pf_consistency = (
                    positive_pf_windows / len(valid_windows)
                )
                pnl_consistency = (
                    positive_pnl_windows / len(valid_windows)
                )
            else:
                pf_consistency = 0.0
                pnl_consistency = 0.0

            aggregate[variant_name] = {
                "development": development_summary,
                "validation": validation_summary,
                "windows_total": len(window_reports),
                "windows_with_enough_trades": len(
                    valid_windows
                ),
                "windows_pf_above_1": positive_pf_windows,
                "windows_pnl_positive": positive_pnl_windows,
                "pf_consistency": pf_consistency,
                "pnl_consistency": pnl_consistency,
            }

        baseline_name = "V1_BASELINE"
        baseline = aggregate[baseline_name]

        for variant_name in aggregate:
            if variant_name == baseline_name:
                continue

            candidate = aggregate[variant_name]

            candidate["vs_baseline"] = {
                "validation_trade_change": (
                    candidate["validation"]["trades"]
                    - baseline["validation"]["trades"]
                ),
                "validation_win_rate_change": (
                    candidate["validation"]["win_rate"]
                    - baseline["validation"]["win_rate"]
                ),
                "validation_profit_factor_change": (
                    self._safe_difference(
                        candidate["validation"][
                            "profit_factor"
                        ],
                        baseline["validation"][
                            "profit_factor"
                        ],
                    )
                ),
                "validation_pnl_change": (
                    candidate["validation"]["total_pnl"]
                    - baseline["validation"]["total_pnl"]
                ),
                "validation_drawdown_change": (
                    candidate["validation"]["max_drawdown"]
                    - baseline["validation"]["max_drawdown"]
                ),
                "pf_consistency_change": (
                    candidate["pf_consistency"]
                    - baseline["pf_consistency"]
                ),
                "pnl_consistency_change": (
                    candidate["pnl_consistency"]
                    - baseline["pnl_consistency"]
                ),
            }

        return {
            "data_start": data["timestamp"].min(),
            "data_end": data["timestamp"].max(),
            "windows": window_reports,
            "aggregate": aggregate,
        }

    @staticmethod
    def _safe_difference(
        first,
        second,
    ):
        if first is None or second is None:
            return None

        return float(first) - float(second)


def format_walk_forward_report(report: Dict) -> str:
    """Create a compact human-readable report."""

    lines = []

    lines.append("")
    lines.append(
        "WALK-FORWARD VALIDATION"
    )
    lines.append("=" * 120)
    lines.append(
        f"Data: {report['data_start']} -> "
        f"{report['data_end']}"
    )
    lines.append(
        f"Windows: {len(report['windows'])}"
    )
    lines.append("")

    lines.append(
        f"{'VARIANT':<32}"
        f"{'VAL TRADES':>12}"
        f"{'WIN RATE':>12}"
        f"{'PF':>12}"
        f"{'P&L':>14}"
        f"{'MAX DD':>12}"
        f"{'PF>1':>10}"
        f"{'PNL>0':>10}"
    )
    lines.append("-" * 114)

    for variant_name, summary in report[
        "aggregate"
    ].items():
        pf = summary["validation"][
            "profit_factor"
        ]

        pf_text = (
            "N/A"
            if pf is None
            else f"{pf:.4f}"
        )

        lines.append(
            f"{variant_name:<32}"
            f"{summary['validation']['trades']:>12}"
            f"{summary['validation']['win_rate']:>12.2%}"
            f"{pf_text:>12}"
            f"{summary['validation']['total_pnl']:>14.2f}"
            f"{summary['validation']['max_drawdown']:>12.2%}"
            f"{summary['windows_pf_above_1']:>10}"
            f"{summary['windows_pnl_positive']:>10}"
        )

    lines.append("")
    lines.append(
        "CONSISTENCY"
    )
    lines.append("-" * 120)

    for variant_name, summary in report[
        "aggregate"
    ].items():
        lines.append(
            f"{variant_name:<32}"
            f"PF>1 consistency: "
            f"{summary['pf_consistency']:.2%} | "
            f"P&L-positive consistency: "
            f"{summary['pnl_consistency']:.2%}"
        )

    lines.append("")
    lines.append(
        "WINDOW DETAILS"
    )
    lines.append("-" * 120)

    for report_item in report["windows"]:
        window = report_item["window"]

        lines.append(
            f"Window {window.index}: "
            f"development "
            f"{window.development_start} -> "
            f"{window.development_end}; "
            f"validation "
            f"{window.validation_start} -> "
            f"{window.validation_end}"
        )

        for variant_name, variant_report in (
            report_item["variants"].items()
        ):
            summary = variant_report[
                "validation"
            ]

            pf = summary["profit_factor"]

            pf_text = (
                "N/A"
                if pf is None
                else f"{pf:.4f}"
            )

            lines.append(
                f"  {variant_name:<30}"
                f"trades={summary['trades']:>3} "
                f"win={summary['win_rate']:.2%} "
                f"PF={pf_text:>7} "
                f"P&L={summary['total_pnl']:+.2f} "
                f"DD={summary['max_drawdown']:.2%}"
            )

    return "\n".join(lines)


if __name__ == "__main__":
    print(
        "WalkForwardEngine module loaded successfully."
    )
