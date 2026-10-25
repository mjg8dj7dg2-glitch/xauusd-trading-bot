import pandas as pd


class RegimeRobustnessAnalyzer:
    """
    Analyze backtest trades by market regime.

    Expected trade columns:
        pnl
        direction
        trend_regime
        volatility_regime
    """

    def __init__(self, minimum_trades=5):
        self.minimum_trades = minimum_trades

    def _prepare(self, trades):
        if trades is None:
            return pd.DataFrame()

        df = pd.DataFrame(trades).copy()

        if df.empty:
            return df

        if "pnl" not in df.columns:
            raise ValueError("Missing required trade column: pnl")

        if "direction" not in df.columns:
            df["direction"] = "UNKNOWN"

        if "trend_regime" not in df.columns:
            df["trend_regime"] = "UNKNOWN"

        if "volatility_regime" not in df.columns:
            df["volatility_regime"] = "UNKNOWN"

        df["pnl"] = pd.to_numeric(
            df["pnl"],
            errors="coerce",
        )

        df = df.dropna(subset=["pnl"]).copy()

        return df

    @staticmethod
    def _profit_factor(pnls):
        gross_profit = pnls[pnls > 0].sum()
        gross_loss = abs(pnls[pnls < 0].sum())

        if gross_loss == 0:
            if gross_profit > 0:
                return float("inf")
            return 0.0

        return float(gross_profit / gross_loss)

    @staticmethod
    def _max_drawdown(pnls):
        if len(pnls) == 0:
            return 0.0

        equity = pnls.cumsum()
        running_peak = equity.cummax()
        drawdown = running_peak - equity

        return float(drawdown.max())

    def _summarize_group(self, group):
        trades = len(group)

        if trades == 0:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "max_drawdown": 0.0,
                "status": "INSUFFICIENT_DATA",
            }

        pnls = group["pnl"]

        wins = int((pnls > 0).sum())
        losses = int((pnls < 0).sum())

        win_rate = wins / trades
        profit_factor = self._profit_factor(pnls)

        total_pnl = float(pnls.sum())
        average_pnl = float(pnls.mean())
        max_drawdown = self._max_drawdown(pnls)

        if trades < self.minimum_trades:
            status = "INSUFFICIENT_DATA"
        elif profit_factor < 1.0:
            status = "WEAK"
        elif total_pnl > 0:
            status = "POSITIVE"
        else:
            status = "WEAK"

        return {
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "total_pnl": total_pnl,
            "average_pnl": average_pnl,
            "max_drawdown": max_drawdown,
            "status": status,
        }

    def analyze_by_column(self, trades, column):
        df = self._prepare(trades)

        if df.empty:
            return pd.DataFrame()

        if column not in df.columns:
            raise ValueError(
                f"Column not found: {column}"
            )

        rows = []

        for value, group in df.groupby(
            column,
            dropna=False,
        ):
            summary = self._summarize_group(group)
            summary[column] = value
            rows.append(summary)

        result = pd.DataFrame(rows)

        columns = [
            column,
            "trades",
            "wins",
            "losses",
            "win_rate",
            "profit_factor",
            "total_pnl",
            "average_pnl",
            "max_drawdown",
            "status",
        ]

        return result[columns].sort_values(
            by=["trades", "total_pnl"],
            ascending=[False, False],
        ).reset_index(drop=True)

    def analyze_by_columns(self, trades, columns):
        df = self._prepare(trades)

        if df.empty:
            return pd.DataFrame()

        for column in columns:
            if column not in df.columns:
                raise ValueError(
                    f"Column not found: {column}"
                )

        rows = []

        for values, group in df.groupby(
            columns,
            dropna=False,
        ):
            if not isinstance(values, tuple):
                values = (values,)

            summary = self._summarize_group(group)

            for column, value in zip(columns, values):
                summary[column] = value

            rows.append(summary)

        result = pd.DataFrame(rows)

        ordered_columns = (
            list(columns)
            + [
                "trades",
                "wins",
                "losses",
                "win_rate",
                "profit_factor",
                "total_pnl",
                "average_pnl",
                "max_drawdown",
                "status",
            ]
        )

        return result[ordered_columns].sort_values(
            by=["trades", "total_pnl"],
            ascending=[False, False],
        ).reset_index(drop=True)

    def analyze_direction(self, trades):
        return self.analyze_by_column(
            trades,
            "direction",
        )

    def analyze_trend_regime(self, trades):
        return self.analyze_by_column(
            trades,
            "trend_regime",
        )

    def analyze_volatility_regime(self, trades):
        return self.analyze_by_column(
            trades,
            "volatility_regime",
        )

    def analyze_trend_and_volatility(self, trades):
        return self.analyze_by_columns(
            trades,
            [
                "trend_regime",
                "volatility_regime",
            ],
        )

    def analyze_direction_and_trend(self, trades):
        return self.analyze_by_columns(
            trades,
            [
                "direction",
                "trend_regime",
            ],
        )

    def analyze_direction_and_volatility(self, trades):
        return self.analyze_by_columns(
            trades,
            [
                "direction",
                "volatility_regime",
            ],
        )

    def analyze_all(self, trades):
        return {
            "direction": self.analyze_direction(trades),
            "trend_regime": self.analyze_trend_regime(
                trades
            ),
            "volatility_regime": (
                self.analyze_volatility_regime(trades)
            ),
            "trend_and_volatility": (
                self.analyze_trend_and_volatility(
                    trades
                )
            ),
            "direction_and_trend": (
                self.analyze_direction_and_trend(
                    trades
                )
            ),
            "direction_and_volatility": (
                self.analyze_direction_and_volatility(
                    trades
                )
            ),
        }

    def find_weak_regimes(self, trades):
        analyses = self.analyze_all(trades)

        weak = {}

        for name, table in analyses.items():
            if table.empty:
                weak[name] = table
                continue

            weak[name] = table[
                (table["trades"] >= self.minimum_trades)
                & (table["profit_factor"] < 1.0)
            ].copy()

        return weak

    def find_positive_regimes(self, trades):
        analyses = self.analyze_all(trades)

        positive = {}

        for name, table in analyses.items():
            if table.empty:
                positive[name] = table
                continue

            positive[name] = table[
                (table["trades"] >= self.minimum_trades)
                & (table["profit_factor"] >= 1.0)
                & (table["total_pnl"] > 0)
            ].copy()

        return positive

    def print_report(self, trades):
        analyses = self.analyze_all(trades)

        print()
        print("=" * 80)
        print("REGIME-AWARE ROBUSTNESS ANALYSIS")
        print("=" * 80)

        for name, table in analyses.items():
            print()
            print(name.upper().replace("_", " "))
            print("-" * 80)

            if table.empty:
                print("No data.")
                continue

            display = table.copy()

            display["win_rate"] = (
                display["win_rate"] * 100
            ).round(2)

            display["profit_factor"] = (
                display["profit_factor"]
                .replace(float("inf"), "INF")
            )

            print(
                display.to_string(index=False)
            )

        print()
        print("=" * 80)
        print("ROBUSTNESS ANALYSIS COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    sample_trades = [
        {
            "pnl": 100.0,
            "direction": "LONG",
            "trend_regime": "TRENDING_UP",
            "volatility_regime": "LOW_VOLATILITY",
        },
        {
            "pnl": -50.0,
            "direction": "SHORT",
            "trend_regime": "TRENDING_DOWN",
            "volatility_regime": "LOW_VOLATILITY",
        },
        {
            "pnl": 75.0,
            "direction": "LONG",
            "trend_regime": "TRENDING_UP",
            "volatility_regime": "NORMAL_VOLATILITY",
        },
        {
            "pnl": -80.0,
            "direction": "SHORT",
            "trend_regime": "RANGING",
            "volatility_regime": "LOW_VOLATILITY",
        },
        {
            "pnl": 50.0,
            "direction": "LONG",
            "trend_regime": "TRENDING_UP",
            "volatility_regime": "LOW_VOLATILITY",
        },
    ]

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=2
    )

    analyzer.print_report(sample_trades)