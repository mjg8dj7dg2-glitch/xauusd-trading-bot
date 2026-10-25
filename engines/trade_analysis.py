import math
from collections import Counter

import pandas as pd


class TradeAnalyzer:
    """
    Analyzes completed backtest trades without changing the strategy.

    The analyzer is intentionally descriptive:
    it measures where the strategy performs well or poorly,
    but does not automatically optimize parameters.
    """

    def __init__(self, trades):
        self.trades = trades or []
        self.df = self._prepare_dataframe()

    def _prepare_dataframe(self):
        if not self.trades:
            return pd.DataFrame()

        df = pd.DataFrame(self.trades).copy()

        numeric_columns = [
            "pnl",
            "entry_price",
            "exit_price",
            "stop_loss",
            "take_profit",
            "quantity",
            "rsi",
            "atr",
            "ema",
            "sma",
            "signal_strength",
            "correlation",
            "mae",
            "mfe",
            "max_adverse_excursion",
            "max_favorable_excursion",
            "duration_minutes",
        ]

        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        datetime_columns = [
            "entry_time",
            "exit_time",
            "timestamp",
        ]

        for column in datetime_columns:
            if column in df.columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce",
                )

        if "result" not in df.columns and "pnl" in df.columns:
            df["result"] = "BREAKEVEN"
            df.loc[df["pnl"] > 0, "result"] = "WIN"
            df.loc[df["pnl"] < 0, "result"] = "LOSS"

        if "direction" not in df.columns:
            if "signal" in df.columns:
                df["direction"] = df["signal"]
            else:
                df["direction"] = "UNKNOWN"

        if "signal" not in df.columns:
            df["signal"] = df["direction"]

        if "trend_regime" not in df.columns:
            df["trend_regime"] = "UNKNOWN"

        if "volatility_regime" not in df.columns:
            df["volatility_regime"] = "UNKNOWN"

        return df

    @staticmethod
    def _safe_profit_factor(pnl):
        if len(pnl) == 0:
            return 0.0

        winning = pnl[pnl > 0].sum()
        losing = abs(pnl[pnl < 0].sum())

        if losing == 0:
            if winning > 0:
                return float("inf")
            return 0.0

        return float(winning / losing)

    @staticmethod
    def _safe_win_rate(pnl):
        if len(pnl) == 0:
            return 0.0

        return float((pnl > 0).mean())

    def _performance(self, dataframe):
        if dataframe.empty:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
            }

        pnl = pd.to_numeric(
            dataframe.get("pnl", pd.Series(dtype=float)),
            errors="coerce",
        ).fillna(0.0)

        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        breakeven = pnl[pnl == 0]

        return {
            "trades": int(len(pnl)),
            "wins": int(len(wins)),
            "losses": int(len(losses)),
            "breakeven": int(len(breakeven)),
            "win_rate": self._safe_win_rate(pnl),
            "profit_factor": self._safe_profit_factor(pnl),
            "total_pnl": float(pnl.sum()),
            "average_pnl": float(pnl.mean()),
            "average_win": float(wins.mean()) if len(wins) else 0.0,
            "average_loss": float(losses.mean()) if len(losses) else 0.0,
            "max_win": float(wins.max()) if len(wins) else 0.0,
            "max_loss": float(losses.min()) if len(losses) else 0.0,
        }

    def overall_performance(self):
        return self._performance(self.df)

    def performance_by_column(self, column):
        if self.df.empty or column not in self.df.columns:
            return {}

        report = {}

        for value, group in self.df.groupby(column, dropna=False):
            key = "UNKNOWN" if pd.isna(value) else str(value)
            report[key] = self._performance(group)

        return report

    def direction_analysis(self):
        return self.performance_by_column("direction")

    def trend_analysis(self):
        return self.performance_by_column("trend_regime")

    def volatility_analysis(self):
        return self.performance_by_column("volatility_regime")

    def exit_reason_analysis(self):
        return self.performance_by_column("exit_reason")

    def result_distribution(self):
        if self.df.empty or "result" not in self.df.columns:
            return {}

        counts = self.df["result"].fillna("UNKNOWN").value_counts()

        return {
            str(key): int(value)
            for key, value in counts.items()
        }

    def _calculate_drawdown(self, dataframe):
        if dataframe.empty or "pnl" not in dataframe.columns:
            return 0.0

        pnl = pd.to_numeric(
            dataframe["pnl"],
            errors="coerce",
        ).fillna(0.0)

        equity = pnl.cumsum()

        if equity.empty:
            return 0.0

        running_peak = equity.cummax()
        drawdown = running_peak - equity

        return float(drawdown.max())

    def time_analysis(self):
        """
        Groups trades by UTC hour when entry_time is available.
        """

        if self.df.empty:
            return {}

        time_column = None

        if "entry_time" in self.df.columns:
            time_column = "entry_time"
        elif "timestamp" in self.df.columns:
            time_column = "timestamp"

        if time_column is None:
            return {}

        working = self.df.dropna(subset=[time_column]).copy()

        if working.empty:
            return {}

        working["entry_hour"] = working[time_column].dt.hour

        report = {}

        for hour, group in working.groupby("entry_hour"):
            result = self._performance(group)
            result["hour"] = int(hour)
            report[str(int(hour))] = result

        return report

    def weekday_analysis(self):
        if self.df.empty:
            return {}

        time_column = None

        if "entry_time" in self.df.columns:
            time_column = "entry_time"
        elif "timestamp" in self.df.columns:
            time_column = "timestamp"

        if time_column is None:
            return {}

        working = self.df.dropna(subset=[time_column]).copy()

        if working.empty:
            return {}

        working["weekday"] = working[time_column].dt.day_name()

        report = {}

        for weekday, group in working.groupby("weekday"):
            report[str(weekday)] = self._performance(group)

        return report

    def indicator_analysis(self):
        """
        Compares average indicator values for winners and losers.
        """

        if self.df.empty:
            return {}

        indicators = [
            "rsi",
            "atr",
            "ema",
            "sma",
            "signal_strength",
            "correlation",
        ]

        report = {}

        for indicator in indicators:
            if indicator not in self.df.columns:
                continue

            values = pd.to_numeric(
                self.df[indicator],
                errors="coerce",
            )

            winners = values[self.df["result"] == "WIN"].dropna()
            losers = values[self.df["result"] == "LOSS"].dropna()

            report[indicator] = {
                "overall_average": (
                    float(values.dropna().mean())
                    if len(values.dropna())
                    else None
                ),
                "winner_average": (
                    float(winners.mean())
                    if len(winners)
                    else None
                ),
                "loser_average": (
                    float(losers.mean())
                    if len(losers)
                    else None
                ),
                "winner_count": int(len(winners)),
                "loser_count": int(len(losers)),
            }

        return report

    def excursion_analysis(self):
        """
        Analyzes MAE/MFE when those fields exist.

        MAE = maximum adverse excursion.
        MFE = maximum favorable excursion.
        """

        if self.df.empty:
            return {}

        mae_column = None
        mfe_column = None

        for column in [
            "mae",
            "max_adverse_excursion",
        ]:
            if column in self.df.columns:
                mae_column = column
                break

        for column in [
            "mfe",
            "max_favorable_excursion",
        ]:
            if column in self.df.columns:
                mfe_column = column
                break

        report = {}

        if mae_column:
            mae = pd.to_numeric(
                self.df[mae_column],
                errors="coerce",
            ).dropna()

            report["mae"] = {
                "count": int(len(mae)),
                "average": float(mae.mean()) if len(mae) else None,
                "median": float(mae.median()) if len(mae) else None,
                "maximum": float(mae.max()) if len(mae) else None,
            }

        if mfe_column:
            mfe = pd.to_numeric(
                self.df[mfe_column],
                errors="coerce",
            ).dropna()

            report["mfe"] = {
                "count": int(len(mfe)),
                "average": float(mfe.mean()) if len(mfe) else None,
                "median": float(mfe.median()) if len(mfe) else None,
                "maximum": float(mfe.max()) if len(mfe) else None,
            }

        return report

    def losing_streaks(self):
        if self.df.empty:
            return {
                "maximum_losing_streak": 0,
                "current_losing_streak": 0,
            }

        results = self.df["result"].fillna("UNKNOWN").tolist()

        maximum_streak = 0
        current_streak = 0

        for result in results:
            if result == "LOSS":
                current_streak += 1
                maximum_streak = max(
                    maximum_streak,
                    current_streak,
                )
            else:
                current_streak = 0

        return {
            "maximum_losing_streak": int(maximum_streak),
            "current_losing_streak": int(current_streak),
        }

    def rolling_performance(self, window=20):
        if self.df.empty or "pnl" not in self.df.columns:
            return []

        pnl = pd.to_numeric(
            self.df["pnl"],
            errors="coerce",
        ).fillna(0.0)

        if len(pnl) < window:
            return []

        records = []

        for end_index in range(window, len(pnl) + 1):
            window_pnl = pnl.iloc[
                end_index - window:end_index
            ]

            records.append(
                {
                    "trade_number": int(end_index),
                    "trades": int(window),
                    "win_rate": self._safe_win_rate(window_pnl),
                    "profit_factor": self._safe_profit_factor(
                        window_pnl
                    ),
                    "total_pnl": float(window_pnl.sum()),
                    "average_pnl": float(window_pnl.mean()),
                }
            )

        return records

    def losing_pattern_summary(self):
        """
        Finds simple recurring categorical conditions among losing trades.

        This is descriptive only. It does not automatically disable
        any condition.
        """

        if self.df.empty:
            return []

        losses = self.df[
            self.df["result"] == "LOSS"
        ].copy()

        if losses.empty:
            return []

        columns = [
            "direction",
            "trend_regime",
            "volatility_regime",
            "exit_reason",
        ]

        patterns = []

        for column in columns:
            if column not in losses.columns:
                continue

            counts = (
                losses[column]
                .fillna("UNKNOWN")
                .value_counts()
            )

            for value, count in counts.items():
                patterns.append(
                    {
                        "type": column,
                        "value": str(value),
                        "loss_count": int(count),
                        "percentage_of_losses": float(
                            count / len(losses)
                        ),
                    }
                )

        patterns.sort(
            key=lambda item: (
                item["loss_count"],
                item["percentage_of_losses"],
            ),
            reverse=True,
        )

        return patterns

    def compare_first_half_second_half(self):
        if self.df.empty:
            return {}

        midpoint = len(self.df) // 2

        first_half = self.df.iloc[:midpoint]
        second_half = self.df.iloc[midpoint:]

        return {
            "first_half": self._performance(first_half),
            "second_half": self._performance(second_half),
        }

    def build_report(self):
        """
        Builds the complete descriptive trade-analysis report.
        """

        if self.df.empty:
            return {
                "trade_count": 0,
                "overall": self._performance(self.df),
                "directions": {},
                "trend_regimes": {},
                "volatility_regimes": {},
                "exit_reasons": {},
                "results": {},
                "time_of_day": {},
                "weekdays": {},
                "indicators": {},
                "excursions": {},
                "losing_streaks": {
                    "maximum_losing_streak": 0,
                    "current_losing_streak": 0,
                },
                "losing_patterns": [],
                "rolling_performance": [],
                "period_comparison": {},
            }

        return {
            "trade_count": int(len(self.df)),
            "overall": self.overall_performance(),
            "directions": self.direction_analysis(),
            "trend_regimes": self.trend_analysis(),
            "volatility_regimes": self.volatility_analysis(),
            "exit_reasons": self.exit_reason_analysis(),
            "results": self.result_distribution(),
            "time_of_day": self.time_analysis(),
            "weekdays": self.weekday_analysis(),
            "indicators": self.indicator_analysis(),
            "excursions": self.excursion_analysis(),
            "losing_streaks": self.losing_streaks(),
            "losing_patterns": self.losing_pattern_summary(),
            "rolling_performance": self.rolling_performance(
                window=20
            ),
            "period_comparison": self.compare_first_half_second_half(),
        }


def analyze_trades(trades):
    """
    Convenience function.
    """

    analyzer = TradeAnalyzer(trades)
    return analyzer.build_report()


def format_number(value, decimals=4):
    if value is None:
        return "N/A"

    if isinstance(value, float) and math.isinf(value):
        return "INF"

    if isinstance(value, float) and math.isnan(value):
        return "N/A"

    return f"{value:.{decimals}f}"


def print_report(report):
    """
    Prints the analysis in a readable format.
    """

    print()
    print("=" * 70)
    print("TRADE ANALYSIS REPORT")
    print("=" * 70)

    print()
    print("OVERALL PERFORMANCE")
    print("-" * 70)

    overall = report["overall"]

    print(f"Trades          : {overall['trades']}")
    print(f"Wins            : {overall['wins']}")
    print(f"Losses          : {overall['losses']}")
    print(f"Breakeven       : {overall['breakeven']}")
    print(
        f"Win rate        : "
        f"{overall['win_rate']:.4f}"
    )
    print(
        f"Profit factor   : "
        f"{format_number(overall['profit_factor'])}"
    )
    print(
        f"Total P&L       : "
        f"{overall['total_pnl']:.2f}"
    )
    print(
        f"Average P&L     : "
        f"{overall['average_pnl']:.2f}"
    )
    print(
        f"Average win     : "
        f"{overall['average_win']:.2f}"
    )
    print(
        f"Average loss    : "
        f"{overall['average_loss']:.2f}"
    )

    print()
    print("DIRECTION ANALYSIS")
    print("-" * 70)

    for direction, data in report["directions"].items():
        print(f"\n{direction}")
        print(f"  Trades       : {data['trades']}")
        print(f"  Win rate     : {data['win_rate']:.4f}")
        print(
            f"  Profit factor: "
            f"{format_number(data['profit_factor'])}"
        )
        print(f"  Total P&L    : {data['total_pnl']:.2f}")
        print(f"  Average P&L  : {data['average_pnl']:.2f}")

    print()
    print("TREND REGIME ANALYSIS")
    print("-" * 70)

    for regime, data in report["trend_regimes"].items():
        print(f"\n{regime}")
        print(f"  Trades       : {data['trades']}")
        print(f"  Win rate     : {data['win_rate']:.4f}")
        print(
            f"  Profit factor: "
            f"{format_number(data['profit_factor'])}"
        )
        print(f"  Total P&L    : {data['total_pnl']:.2f}")

    print()
    print("VOLATILITY REGIME ANALYSIS")
    print("-" * 70)

    for regime, data in report["volatility_regimes"].items():
        print(f"\n{regime}")
        print(f"  Trades       : {data['trades']}")
        print(f"  Win rate     : {data['win_rate']:.4f}")
        print(
            f"  Profit factor: "
            f"{format_number(data['profit_factor'])}"
        )
        print(f"  Total P&L    : {data['total_pnl']:.2f}")

    print()
    print("EXIT REASON ANALYSIS")
    print("-" * 70)

    for reason, data in report["exit_reasons"].items():
        print(f"\n{reason}")
        print(f"  Trades       : {data['trades']}")
        print(f"  Win rate     : {data['win_rate']:.4f}")
        print(
            f"  Profit factor: "
            f"{format_number(data['profit_factor'])}"
        )
        print(f"  Total P&L    : {data['total_pnl']:.2f}")

    print()
    print("LOSING STREAKS")
    print("-" * 70)

    streaks = report["losing_streaks"]

    print(
        f"Maximum losing streak: "
        f"{streaks['maximum_losing_streak']}"
    )
    print(
        f"Current losing streak: "
        f"{streaks['current_losing_streak']}"
    )

    print()
    print("INDICATOR COMPARISON")
    print("-" * 70)

    for indicator, data in report["indicators"].items():
        print(f"\n{indicator}")
        print(
            f"  Overall average: "
            f"{format_number(data['overall_average'])}"
        )
        print(
            f"  Winner average : "
            f"{format_number(data['winner_average'])}"
        )
        print(
            f"  Loser average  : "
            f"{format_number(data['loser_average'])}"
        )

    print()
    print("RECURRING LOSING PATTERNS")
    print("-" * 70)

    patterns = report["losing_patterns"]

    if not patterns:
        print("No recurring losing patterns detected.")

    for pattern in patterns[:20]:
        print(
            f"{pattern['type']} = {pattern['value']} | "
            f"losses={pattern['loss_count']} | "
            f"{pattern['percentage_of_losses']:.2%} of losses"
        )

    print()
    print("FIRST HALF VS SECOND HALF")
    print("-" * 70)

    comparison = report["period_comparison"]

    if comparison:
        first = comparison["first_half"]
        second = comparison["second_half"]

        print("First half:")
        print(f"  Trades       : {first['trades']}")
        print(f"  Win rate     : {first['win_rate']:.4f}")
        print(
            f"  Profit factor: "
            f"{format_number(first['profit_factor'])}"
        )
        print(f"  Total P&L    : {first['total_pnl']:.2f}")

        print("\nSecond half:")
        print(f"  Trades       : {second['trades']}")
        print(f"  Win rate     : {second['win_rate']:.4f}")
        print(
            f"  Profit factor: "
            f"{format_number(second['profit_factor'])}"
        )
        print(f"  Total P&L    : {second['total_pnl']:.2f}")

    print()
    print("=" * 70)
    print("TRADE ANALYSIS COMPLETE")
    print("=" * 70)