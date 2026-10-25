import itertools

import pandas as pd


class MultiConditionPatternAnalyzer:
    """
    Finds recurring combinations of trade conditions.

    This module is descriptive only.
    It does not modify, optimize, disable, or enable strategy rules.
    """

    def __init__(
        self,
        trades,
        minimum_trades=5,
        minimum_losses=3,
        minimum_wins=3,
    ):
        self.trades = trades or []
        self.minimum_trades = int(minimum_trades)
        self.minimum_losses = int(minimum_losses)
        self.minimum_wins = int(minimum_wins)
        self.df = self._prepare_dataframe()

    def _prepare_dataframe(self):
        if not self.trades:
            return pd.DataFrame()

        df = pd.DataFrame(self.trades).copy()

        numeric_columns = [
            "pnl",
            "rsi",
            "atr",
            "entry_price",
            "exit_price",
            "signal_strength",
        ]

        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce",
                )

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

        if "result" not in df.columns:
            if "pnl" in df.columns:
                df["result"] = "BREAKEVEN"

                df.loc[
                    df["pnl"] > 0,
                    "result",
                ] = "WIN"

                df.loc[
                    df["pnl"] < 0,
                    "result",
                ] = "LOSS"
            else:
                df["result"] = "UNKNOWN"

        if "direction" not in df.columns:
            if "signal" in df.columns:
                df["direction"] = df["signal"]
            else:
                df["direction"] = "UNKNOWN"

        if "trend_regime" not in df.columns:
            df["trend_regime"] = "UNKNOWN"

        if "volatility_regime" not in df.columns:
            df["volatility_regime"] = "UNKNOWN"

        self._add_time_features(df)
        self._add_rsi_zones(df)
        self._add_atr_zones(df)

        return df

    @staticmethod
    def _add_time_features(df):
        time_column = None

        if "entry_time" in df.columns:
            time_column = "entry_time"
        elif "timestamp" in df.columns:
            time_column = "timestamp"

        if time_column is None:
            df["entry_hour"] = -1
            df["weekday"] = "UNKNOWN"
            return

        timestamps = df[time_column]

        df["entry_hour"] = timestamps.dt.hour.fillna(-1).astype(int)

        df["weekday"] = timestamps.dt.day_name()

        df["weekday"] = df["weekday"].fillna("UNKNOWN")

    @staticmethod
    def _add_rsi_zones(df):
        if "rsi" not in df.columns:
            df["rsi_zone"] = "UNKNOWN"
            return

        rsi = df["rsi"]

        conditions = [
            rsi < 30,
            (rsi >= 30) & (rsi < 40),
            (rsi >= 40) & (rsi < 50),
            (rsi >= 50) & (rsi < 60),
            (rsi >= 60) & (rsi < 70),
            rsi >= 70,
        ]

        labels = [
            "RSI_BELOW_30",
            "RSI_30_40",
            "RSI_40_50",
            "RSI_50_60",
            "RSI_60_70",
            "RSI_70_PLUS",
        ]

        df["rsi_zone"] = pd.Series(
            pd.cut(
                rsi,
                bins=[
                    float("-inf"),
                    30,
                    40,
                    50,
                    60,
                    70,
                    float("inf"),
                ],
                labels=labels,
                right=False,
            ),
            index=df.index,
        )

        df["rsi_zone"] = (
            df["rsi_zone"]
            .astype("object")
            .where(
                df["rsi_zone"].notna(),
                "UNKNOWN",
            )
        )

    @staticmethod
    def _add_atr_zones(df):
        if "atr" not in df.columns:
            df["atr_zone"] = "UNKNOWN"
            return

        atr = df["atr"]

        # These are descriptive fixed zones based on the
        # current XAUUSD analysis. They are NOT optimized values.
        df["atr_zone"] = pd.cut(
            atr,
            bins=[
                float("-inf"),
                5.0,
                8.0,
                12.0,
                16.0,
                float("inf"),
            ],
            labels=[
                "ATR_BELOW_5",
                "ATR_5_8",
                "ATR_8_12",
                "ATR_12_16",
                "ATR_16_PLUS",
            ],
            right=False,
        )

        df["atr_zone"] = (
            df["atr_zone"]
            .astype("object")
            .where(
                df["atr_zone"].notna(),
                "UNKNOWN",
            )
        )

    @staticmethod
    def _performance(group):
        if group.empty:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
            }

        pnl = pd.to_numeric(
            group["pnl"],
            errors="coerce",
        ).fillna(0.0)

        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        gross_profit = float(wins.sum())
        gross_loss = abs(float(losses.sum()))

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        return {
            "trades": int(len(group)),
            "wins": int(len(wins)),
            "losses": int(len(losses)),
            "win_rate": float(
                (pnl > 0).mean()
            ),
            "profit_factor": float(
                profit_factor
            ),
            "total_pnl": float(
                pnl.sum()
            ),
            "average_pnl": float(
                pnl.mean()
            ),
        }

    def _condition_columns(self):
        possible_columns = [
            "direction",
            "trend_regime",
            "volatility_regime",
            "weekday",
            "entry_hour",
            "rsi_zone",
            "atr_zone",
        ]

        return [
            column
            for column in possible_columns
            if column in self.df.columns
        ]

    def analyze_single_conditions(self):
        """
        Performance of each individual condition.
        """

        if self.df.empty:
            return {}

        report = {}

        for column in self._condition_columns():
            column_report = {}

            for value, group in self.df.groupby(
                column,
                dropna=False,
            ):
                key = (
                    "UNKNOWN"
                    if pd.isna(value)
                    else str(value)
                )

                metrics = self._performance(group)

                if metrics["trades"] >= self.minimum_trades:
                    column_report[key] = metrics

            report[column] = column_report

        return report

    def _build_combination(self, columns):
        """
        Build combinations of two or more conditions.
        """

        if self.df.empty:
            return []

        results = []

        grouped = self.df.groupby(
            list(columns),
            dropna=False,
        )

        for values, group in grouped:
            metrics = self._performance(group)

            if metrics["trades"] < self.minimum_trades:
                continue

            if len(columns) == 1:
                values = (values,)

            conditions = {}

            for column, value in zip(
                columns,
                values,
            ):
                if pd.isna(value):
                    value = "UNKNOWN"

                conditions[column] = str(value)

            results.append(
                {
                    "conditions": conditions,
                    **metrics,
                }
            )

        return results

    def analyze_combinations(
        self,
        minimum_conditions=2,
        maximum_conditions=3,
    ):
        """
        Analyze combinations of 2–3 conditions by default.
        """

        if self.df.empty:
            return []

        columns = self._condition_columns()

        all_results = []

        maximum_conditions = min(
            maximum_conditions,
            len(columns),
        )

        for combination_size in range(
            minimum_conditions,
            maximum_conditions + 1,
        ):
            for combination in itertools.combinations(
                columns,
                combination_size,
            ):
                results = self._build_combination(
                    combination
                )

                for result in results:
                    result["condition_count"] = (
                        combination_size
                    )

                all_results.extend(results)

        return all_results

    def analyze_loss_patterns(self):
        """
        Finds combinations containing a meaningful number of losses.

        These are candidates for investigation, not automatic filters.
        """

        combinations = self.analyze_combinations(
            minimum_conditions=2,
            maximum_conditions=3,
        )

        patterns = []

        for result in combinations:
            if result["losses"] < self.minimum_losses:
                continue

            patterns.append(result)

        patterns.sort(
            key=lambda item: (
                item["total_pnl"],
                item["profit_factor"],
            )
        )

        return patterns

    def analyze_win_patterns(self):
        """
        Finds combinations containing a meaningful number of wins.
        """

        combinations = self.analyze_combinations(
            minimum_conditions=2,
            maximum_conditions=3,
        )

        patterns = []

        for result in combinations:
            if result["wins"] < self.minimum_wins:
                continue

            patterns.append(result)

        patterns.sort(
            key=lambda item: (
                item["total_pnl"],
                item["profit_factor"],
            ),
            reverse=True,
        )

        return patterns

    def compare_direction_conditions(self):
        """
        Separately analyzes LONG and SHORT combinations.

        This helps determine whether a pattern is direction-specific.
        """

        if self.df.empty:
            return {}

        report = {}

        for direction in [
            "LONG",
            "SHORT",
        ]:
            subset = self.df[
                self.df["direction"].astype(str).str.upper()
                == direction
            ].copy()

            if len(subset) < self.minimum_trades:
                report[direction] = {
                    "trades": int(len(subset)),
                    "patterns": [],
                }
                continue

            original_df = self.df
            self.df = subset

            patterns = self.analyze_combinations(
                minimum_conditions=2,
                maximum_conditions=3,
            )

            self.df = original_df

            patterns.sort(
                key=lambda item: (
                    item["total_pnl"],
                    item["profit_factor"],
                ),
                reverse=True,
            )

            report[direction] = {
                "trades": int(len(subset)),
                "patterns": patterns,
            }

        return report

    def strongest_loss_patterns(self, limit=20):
        patterns = self.analyze_loss_patterns()

        return patterns[:limit]

    def strongest_win_patterns(self, limit=20):
        patterns = self.analyze_win_patterns()

        return patterns[:limit]

    def build_report(self):
        if self.df.empty:
            return {
                "trade_count": 0,
                "single_conditions": {},
                "loss_patterns": [],
                "win_patterns": [],
                "direction_patterns": {},
            }

        return {
            "trade_count": int(len(self.df)),
            "single_conditions": (
                self.analyze_single_conditions()
            ),
            "loss_patterns": (
                self.strongest_loss_patterns()
            ),
            "win_patterns": (
                self.strongest_win_patterns()
            ),
            "direction_patterns": (
                self.compare_direction_conditions()
            ),
        }


def analyze_patterns(
    trades,
    minimum_trades=5,
    minimum_losses=3,
    minimum_wins=3,
):
    analyzer = MultiConditionPatternAnalyzer(
        trades=trades,
        minimum_trades=minimum_trades,
        minimum_losses=minimum_losses,
        minimum_wins=minimum_wins,
    )

    return analyzer.build_report()


def _format_profit_factor(value):
    if value == float("inf"):
        return "INF"

    return f"{value:.4f}"


def print_pattern_list(
    title,
    patterns,
    limit=20,
):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    if not patterns:
        print("No patterns met the minimum sample requirements.")
        return

    for index, pattern in enumerate(
        patterns[:limit],
        start=1,
    ):
        conditions = pattern["conditions"]

        condition_text = " + ".join(
            f"{key}={value}"
            for key, value in conditions.items()
        )

        print()
        print(
            f"{index}. {condition_text}"
        )
        print(
            f"   Trades        : "
            f"{pattern['trades']}"
        )
        print(
            f"   Wins          : "
            f"{pattern['wins']}"
        )
        print(
            f"   Losses        : "
            f"{pattern['losses']}"
        )
        print(
            f"   Win rate      : "
            f"{pattern['win_rate']:.4f}"
        )
        print(
            f"   Profit factor : "
            f"{_format_profit_factor(pattern['profit_factor'])}"
        )
        print(
            f"   Total P&L     : "
            f"{pattern['total_pnl']:.2f}"
        )
        print(
            f"   Average P&L   : "
            f"{pattern['average_pnl']:.2f}"
        )


def print_single_conditions(
    single_conditions,
):
    print()
    print("=" * 70)
    print("SINGLE-CONDITION PERFORMANCE")
    print("=" * 70)

    for column, values in single_conditions.items():
        print()
        print(column)
        print("-" * 70)

        if not values:
            print("No conditions met the minimum sample size.")
            continue

        for value, metrics in values.items():
            print(
                f"{value:25s} | "
                f"trades={metrics['trades']:3d} | "
                f"win_rate={metrics['win_rate']:.4f} | "
                f"PF={_format_profit_factor(metrics['profit_factor'])} | "
                f"P&L={metrics['total_pnl']:.2f}"
            )


def print_direction_patterns(
    direction_patterns,
):
    print()
    print("=" * 70)
    print("DIRECTION-SPECIFIC PATTERNS")
    print("=" * 70)

    for direction, data in direction_patterns.items():
        print()
        print(
            f"{direction} "
            f"({data['trades']} trades)"
        )
        print("-" * 70)

        patterns = data["patterns"]

        if not patterns:
            print("No patterns met the minimum sample size.")
            continue

        for index, pattern in enumerate(
            patterns[:10],
            start=1,
        ):
            conditions = pattern["conditions"]

            condition_text = " + ".join(
                f"{key}={value}"
                for key, value in conditions.items()
            )

            print(
                f"{index}. {condition_text}"
            )
            print(
                f"   trades={pattern['trades']} | "
                f"wins={pattern['wins']} | "
                f"losses={pattern['losses']} | "
                f"PF={_format_profit_factor(pattern['profit_factor'])} | "
                f"P&L={pattern['total_pnl']:.2f}"
            )


def print_report(report):
    print()
    print("=" * 70)
    print("MULTI-CONDITION PATTERN ANALYSIS")
    print("=" * 70)

    print(
        f"\nTrades analyzed: "
        f"{report['trade_count']}"
    )

    print_single_conditions(
        report["single_conditions"]
    )

    print_pattern_list(
        "STRONGEST RECURRING LOSS PATTERNS",
        report["loss_patterns"],
        limit=20,
    )

    print_pattern_list(
        "STRONGEST RECURRING WIN PATTERNS",
        report["win_patterns"],
        limit=20,
    )

    print_direction_patterns(
        report["direction_patterns"]
    )