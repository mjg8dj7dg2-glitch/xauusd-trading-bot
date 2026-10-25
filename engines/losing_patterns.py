import pandas as pd


class LosingPatternDetector:

    def __init__(
        self,
        minimum_losses=3,
        minimum_occurrences=2,
        minimum_percentage=0.50,
    ):
        self.minimum_losses = minimum_losses
        self.minimum_occurrences = minimum_occurrences
        self.minimum_percentage = minimum_percentage

    def _percentage(self, count, total):
        if total <= 0:
            return 0.0

        return count / total

    def analyze(
        self,
        trades,
    ):
        """
        Analyze historical losing trades and identify
        recurring categorical conditions.
        """

        if not trades:
            return {
                "total_trades": 0,
                "losing_trades": 0,
                "loss_rate": 0.0,
                "patterns": [],
            }

        dataframe = pd.DataFrame(trades)

        if "pnl" not in dataframe.columns:
            return {
                "total_trades": len(dataframe),
                "losing_trades": 0,
                "loss_rate": 0.0,
                "patterns": [],
            }

        dataframe["pnl"] = pd.to_numeric(
            dataframe["pnl"],
            errors="coerce",
        )

        dataframe = dataframe.dropna(
            subset=["pnl"]
        )

        total_trades = len(dataframe)

        losing = dataframe[
            dataframe["pnl"] < 0
        ].copy()

        losing_trades = len(losing)

        if losing_trades == 0:
            return {
                "total_trades": total_trades,
                "losing_trades": 0,
                "loss_rate": 0.0,
                "patterns": [],
            }

        loss_rate = (
            losing_trades / total_trades
        )

        patterns = []

        categorical_fields = [
            "direction",
            "trend_regime",
            "volatility_regime",
            "signal_reason",
        ]

        for field in categorical_fields:

            if field not in losing.columns:
                continue

            values = losing[field].dropna()

            if values.empty:
                continue

            counts = values.value_counts()

            for value, count in counts.items():

                percentage = self._percentage(
                    count,
                    losing_trades,
                )

                if (
                    count
                    >= self.minimum_occurrences
                    and percentage
                    >= self.minimum_percentage
                ):

                    patterns.append(
                        {
                            "field": field,
                            "value": value,
                            "occurrences": int(
                                count
                            ),
                            "percentage_of_losses": (
                                float(
                                    percentage
                                )
                            ),
                        }
                    )

        numeric_fields = [
            "rsi",
            "atr",
            "correlation",
        ]

        for field in numeric_fields:

            if field not in losing.columns:
                continue

            values = pd.to_numeric(
                losing[field],
                errors="coerce",
            ).dropna()

            if values.empty:
                continue

            patterns.append(
                {
                    "field": field,
                    "value": "LOSS_AVERAGE",
                    "occurrences": len(values),
                    "percentage_of_losses": 1.0,
                    "average": float(
                        values.mean()
                    ),
                    "minimum": float(
                        values.min()
                    ),
                    "maximum": float(
                        values.max()
                    ),
                }
            )

        patterns.sort(
            key=lambda pattern: (
                pattern[
                    "percentage_of_losses"
                ],
                pattern["occurrences"],
            ),
            reverse=True,
        )

        return {
            "total_trades": total_trades,
            "losing_trades": losing_trades,
            "loss_rate": loss_rate,
            "patterns": patterns,
        }

    def analyze_recent_losses(
        self,
        trades,
        recent_count=10,
    ):
        """
        Analyze only the most recent trades.
        """

        recent_trades = list(trades)[
            -recent_count:
        ]

        return self.analyze(
            recent_trades
        )