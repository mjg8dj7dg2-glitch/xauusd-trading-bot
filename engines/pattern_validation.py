import pandas as pd


class PatternValidationAnalyzer:
    """
    Chronologically validates discovered trading patterns.

    The analyzer splits trades into:
        1. Discovery period
        2. Validation period

    Patterns are discovered only from the discovery period.
    The validation period is then checked independently.

    This module does NOT modify strategy rules.
    """

    def __init__(
        self,
        trades,
        discovery_fraction=0.70,
        minimum_discovery_trades=5,
        minimum_validation_trades=3,
    ):
        self.trades = trades or []
        self.discovery_fraction = float(
            discovery_fraction
        )
        self.minimum_discovery_trades = int(
            minimum_discovery_trades
        )
        self.minimum_validation_trades = int(
            minimum_validation_trades
        )

        self.df = self._prepare_dataframe()

    def _prepare_dataframe(self):
        if not self.trades:
            return pd.DataFrame()

        df = pd.DataFrame(
            self.trades
        ).copy()

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

        df["entry_hour"] = (
            timestamps.dt.hour
            .fillna(-1)
            .astype(int)
        )

        df["weekday"] = (
            timestamps.dt.day_name()
        )

        df["weekday"] = (
            df["weekday"]
            .fillna("UNKNOWN")
        )

    @staticmethod
    def _add_rsi_zones(df):
        if "rsi" not in df.columns:
            df["rsi_zone"] = "UNKNOWN"
            return

        rsi = df["rsi"]

        df["rsi_zone"] = pd.cut(
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
            labels=[
                "RSI_BELOW_30",
                "RSI_30_40",
                "RSI_40_50",
                "RSI_50_60",
                "RSI_60_70",
                "RSI_70_PLUS",
            ],
            right=False,
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

        gross_profit = float(
            wins.sum()
        )

        gross_loss = abs(
            float(losses.sum())
        )

        if gross_loss > 0:
            profit_factor = (
                gross_profit
                / gross_loss
            )
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

    def split_data(self):
        """
        Chronologically split trades into discovery
        and validation periods.
        """

        if self.df.empty:
            return (
                pd.DataFrame(),
                pd.DataFrame(),
            )

        df = self.df.copy()

        time_column = None

        if "entry_time" in df.columns:
            time_column = "entry_time"
        elif "timestamp" in df.columns:
            time_column = "timestamp"

        if time_column is not None:
            df = df.sort_values(
                time_column
            ).reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)

        split_index = int(
            len(df)
            * self.discovery_fraction
        )

        split_index = max(
            1,
            min(
                split_index,
                len(df) - 1,
            ),
        )

        discovery = df.iloc[
            :split_index
        ].copy()

        validation = df.iloc[
            split_index:
        ].copy()

        return discovery, validation

    @staticmethod
    def _condition_columns():
        return [
            "direction",
            "trend_regime",
            "volatility_regime",
            "weekday",
            "entry_hour",
            "rsi_zone",
            "atr_zone",
        ]

    def _available_columns(self, df):
        return [
            column
            for column in self._condition_columns()
            if column in df.columns
        ]

    def _discover_patterns(
        self,
        discovery_df,
        minimum_conditions=2,
        maximum_conditions=3,
    ):
        """
        Discover recurring combinations using ONLY
        the discovery dataset.
        """

        if discovery_df.empty:
            return []

        columns = self._available_columns(
            discovery_df
        )

        results = []

        import itertools

        maximum_conditions = min(
            maximum_conditions,
            len(columns),
        )

        for condition_count in range(
            minimum_conditions,
            maximum_conditions + 1,
        ):
            for combination in itertools.combinations(
                columns,
                condition_count,
            ):
                grouped = discovery_df.groupby(
                    list(combination),
                    dropna=False,
                )

                for values, group in grouped:
                    metrics = self._performance(
                        group
                    )

                    if (
                        metrics["trades"]
                        < self.minimum_discovery_trades
                    ):
                        continue

                    if condition_count == 1:
                        values = (
                            values,
                        )

                    conditions = {}

                    for column, value in zip(
                        combination,
                        values,
                    ):
                        if pd.isna(value):
                            value = "UNKNOWN"

                        conditions[column] = str(
                            value
                        )

                    results.append(
                        {
                            "conditions": conditions,
                            "condition_count": condition_count,
                            "discovery": metrics,
                        }
                    )

        return results

    @staticmethod
    def _matches_conditions(
        df,
        conditions,
    ):
        if df.empty:
            return df

        mask = pd.Series(
            True,
            index=df.index,
        )

        for column, value in conditions.items():
            if column not in df.columns:
                return df.iloc[0:0]

            if value == "UNKNOWN":
                mask &= (
                    df[column]
                    .isna()
                    | (
                        df[column]
                        .astype(str)
                        == "UNKNOWN"
                    )
                )
            else:
                mask &= (
                    df[column]
                    .astype(str)
                    == str(value)
                )

        return df.loc[mask]

    def validate_pattern(
        self,
        pattern,
        validation_df,
    ):
        conditions = pattern[
            "conditions"
        ]

        matching_trades = (
            self._matches_conditions(
                validation_df,
                conditions,
            )
        )

        validation_metrics = (
            self._performance(
                matching_trades
            )
        )

        return {
            "conditions": conditions,
            "condition_count": pattern[
                "condition_count"
            ],
            "discovery": pattern[
                "discovery"
            ],
            "validation": validation_metrics,
        }

    def validate_patterns(
        self,
        minimum_conditions=2,
        maximum_conditions=3,
    ):
        discovery_df, validation_df = (
            self.split_data()
        )

        if (
            discovery_df.empty
            or validation_df.empty
        ):
            return {
                "discovery_trades": len(
                    discovery_df
                ),
                "validation_trades": len(
                    validation_df
                ),
                "validated_patterns": [],
            }

        discovered_patterns = (
            self._discover_patterns(
                discovery_df=discovery_df,
                minimum_conditions=minimum_conditions,
                maximum_conditions=maximum_conditions,
            )
        )

        validated_patterns = []

        for pattern in discovered_patterns:
            result = self.validate_pattern(
                pattern,
                validation_df,
            )

            if (
                result["validation"]["trades"]
                >= self.minimum_validation_trades
            ):
                validated_patterns.append(
                    result
                )

        return {
            "discovery_trades": len(
                discovery_df
            ),
            "validation_trades": len(
                validation_df
            ),
            "discovery_start": (
                discovery_df["entry_time"].iloc[0]
                if "entry_time" in discovery_df.columns
                and not discovery_df.empty
                else None
            ),
            "discovery_end": (
                discovery_df["entry_time"].iloc[-1]
                if "entry_time" in discovery_df.columns
                and not discovery_df.empty
                else None
            ),
            "validation_start": (
                validation_df["entry_time"].iloc[0]
                if "entry_time" in validation_df.columns
                and not validation_df.empty
                else None
            ),
            "validation_end": (
                validation_df["entry_time"].iloc[-1]
                if "entry_time" in validation_df.columns
                and not validation_df.empty
                else None
            ),
            "validated_patterns": validated_patterns,
        }

    @staticmethod
    def _is_positive(
        metrics
    ):
        return (
            metrics["trades"]
            >= 1
            and metrics["profit_factor"]
            > 1.0
            and metrics["total_pnl"]
            > 0
        )

    @staticmethod
    def _is_negative(
        metrics
    ):
        return (
            metrics["trades"]
            >= 1
            and metrics["profit_factor"]
            < 1.0
            and metrics["total_pnl"]
            < 0
        )

    def classify_stability(
        self,
        validated_pattern,
    ):
        discovery = validated_pattern[
            "discovery"
        ]

        validation = validated_pattern[
            "validation"
        ]

        discovery_positive = (
            self._is_positive(
                discovery
            )
        )

        discovery_negative = (
            self._is_negative(
                discovery
            )
        )

        validation_positive = (
            self._is_positive(
                validation
            )
        )

        validation_negative = (
            self._is_negative(
                validation
            )
        )

        if (
            discovery_positive
            and validation_positive
        ):
            return "POSITIVE_STABLE"

        if (
            discovery_negative
            and validation_negative
        ):
            return "NEGATIVE_STABLE"

        if (
            discovery_positive
            and validation_negative
        ):
            return "REVERSED_TO_NEGATIVE"

        if (
            discovery_negative
            and validation_positive
        ):
            return "REVERSED_TO_POSITIVE"

        return "MIXED"

    def build_report(self):
        result = self.validate_patterns()

        for pattern in result[
            "validated_patterns"
        ]:
            pattern["stability"] = (
                self.classify_stability(
                    pattern
                )
            )

        return result


def _format_pf(value):
    if value == float("inf"):
        return "INF"

    return f"{value:.4f}"


def print_validation_report(
    report,
    limit=30,
):
    print()
    print("=" * 70)
    print(
        "OUT-OF-SAMPLE PATTERN VALIDATION"
    )
    print("=" * 70)

    print()
    print(
        f"Discovery trades : "
        f"{report['discovery_trades']}"
    )

    print(
        f"Validation trades: "
        f"{report['validation_trades']}"
    )

    if report.get(
        "discovery_start"
    ) is not None:
        print(
            f"Discovery period : "
            f"{report['discovery_start']} "
            f"-> "
            f"{report['discovery_end']}"
        )

    if report.get(
        "validation_start"
    ) is not None:
        print(
            f"Validation period: "
            f"{report['validation_start']} "
            f"-> "
            f"{report['validation_end']}"
        )

    patterns = report[
        "validated_patterns"
    ]

    if not patterns:
        print()
        print(
            "No patterns had enough validation trades."
        )
        return

    stable_patterns = [
        pattern
        for pattern in patterns
        if pattern["stability"]
        in [
            "POSITIVE_STABLE",
            "NEGATIVE_STABLE",
        ]
    ]

    print()
    print(
        f"Patterns with sufficient validation data: "
        f"{len(patterns)}"
    )

    print(
        f"Stable-direction patterns: "
        f"{len(stable_patterns)}"
    )

    # ---------------------------------------------------------
    # NEGATIVE STABLE
    # ---------------------------------------------------------

    negative = [
        pattern
        for pattern in patterns
        if pattern["stability"]
        == "NEGATIVE_STABLE"
    ]

    negative.sort(
        key=lambda item: (
            item["validation"]["total_pnl"]
        )
    )

    print()
    print("=" * 70)
    print(
        "NEGATIVE PATTERNS THAT PERSISTED "
        "IN VALIDATION"
    )
    print("=" * 70)

    if not negative:
        print(
            "No negative patterns remained negative "
            "in the validation period."
        )
    else:
        for index, pattern in enumerate(
            negative[:limit],
            start=1,
        ):
            conditions = " + ".join(
                f"{key}={value}"
                for key, value
                in pattern[
                    "conditions"
                ].items()
            )

            discovery = pattern[
                "discovery"
            ]

            validation = pattern[
                "validation"
            ]

            print()
            print(
                f"{index}. {conditions}"
            )

            print(
                "   Discovery : "
                f"trades={discovery['trades']} | "
                f"win_rate={discovery['win_rate']:.4f} | "
                f"PF={_format_pf(discovery['profit_factor'])} | "
                f"P&L={discovery['total_pnl']:.2f}"
            )

            print(
                "   Validation: "
                f"trades={validation['trades']} | "
                f"win_rate={validation['win_rate']:.4f} | "
                f"PF={_format_pf(validation['profit_factor'])} | "
                f"P&L={validation['total_pnl']:.2f}"
            )

    # ---------------------------------------------------------
    # POSITIVE STABLE
    # ---------------------------------------------------------

    positive = [
        pattern
        for pattern in patterns
        if pattern["stability"]
        == "POSITIVE_STABLE"
    ]

    positive.sort(
        key=lambda item: (
            item["validation"]["total_pnl"]
        ),
        reverse=True,
    )

    print()
    print("=" * 70)
    print(
        "POSITIVE PATTERNS THAT PERSISTED "
        "IN VALIDATION"
    )
    print("=" * 70)

    if not positive:
        print(
            "No positive patterns remained positive "
            "in the validation period."
        )
    else:
        for index, pattern in enumerate(
            positive[:limit],
            start=1,
        ):
            conditions = " + ".join(
                f"{key}={value}"
                for key, value
                in pattern[
                    "conditions"
                ].items()
            )

            discovery = pattern[
                "discovery"
            ]

            validation = pattern[
                "validation"
            ]

            print()
            print(
                f"{index}. {conditions}"
            )

            print(
                "   Discovery : "
                f"trades={discovery['trades']} | "
                f"win_rate={discovery['win_rate']:.4f} | "
                f"PF={_format_pf(discovery['profit_factor'])} | "
                f"P&L={discovery['total_pnl']:.2f}"
            )

            print(
                "   Validation: "
                f"trades={validation['trades']} | "
                f"win_rate={validation['win_rate']:.4f} | "
                f"PF={_format_pf(validation['profit_factor'])} | "
                f"P&L={validation['total_pnl']:.2f}"
            )

    # ---------------------------------------------------------
    # REVERSED PATTERNS
    # ---------------------------------------------------------

    reversed_patterns = [
        pattern
        for pattern in patterns
        if pattern["stability"]
        in [
            "REVERSED_TO_NEGATIVE",
            "REVERSED_TO_POSITIVE",
        ]
    ]

    print()
    print("=" * 70)
    print(
        "PATTERNS THAT REVERSED"
    )
    print("=" * 70)

    if not reversed_patterns:
        print(
            "No discovered patterns reversed "
            "direction in validation."
        )
    else:
        for index, pattern in enumerate(
            reversed_patterns[:limit],
            start=1,
        ):
            conditions = " + ".join(
                f"{key}={value}"
                for key, value
                in pattern[
                    "conditions"
                ].items()
            )

            print()
            print(
                f"{index}. {conditions}"
            )

            print(
                f"   Stability: "
                f"{pattern['stability']}"
            )

            print(
                f"   Discovery P&L: "
                f"{pattern['discovery']['total_pnl']:.2f}"
            )

            print(
                f"   Validation P&L: "
                f"{pattern['validation']['total_pnl']:.2f}"
            )