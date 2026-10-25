import pandas as pd

from engines.historical_data import HistoricalDataLoader
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals


class HistoricalPipeline:
    """
    Loads historical OHLC data and runs the analysis stages
    required by the trading system.
    """

    def __init__(self, minimum_rows=100):
        self.loader = HistoricalDataLoader(
            minimum_rows=minimum_rows
        )

    def load_data(self, file_path):
        """
        Load and validate historical CSV data.
        """
        return self.loader.load_csv(file_path)

    def analyze(self, df):
        """
        Run technical analysis, market regime analysis,
        volatility analysis, and signal generation.
        """

        if df is None or df.empty:
            raise ValueError(
                "Historical data is empty."
            )

        result = df.copy()

        result = add_technical_features(result)

        result = add_market_regime(result)

        result = generate_signals(result)

        return result

    def run(self, file_path):
        """
        Load a historical CSV and run the complete
        analysis pipeline.
        """

        historical_data = self.load_data(
            file_path
        )

        analyzed_data = self.analyze(
            historical_data
        )

        summary = self.build_summary(
            analyzed_data
        )

        return {
            "data": analyzed_data,
            "summary": summary,
        }

    def build_summary(self, df):
        """
        Build a compact summary of the analyzed data.
        """

        summary = {
            "rows": len(df),
            "start": None,
            "end": None,
            "long_signals": 0,
            "short_signals": 0,
            "no_signals": 0,
            "trending_up": 0,
            "trending_down": 0,
            "ranging": 0,
            "low_volatility": 0,
            "normal_volatility": 0,
            "high_volatility": 0,
            "unknown_volatility": 0,
        }

        if df.empty:
            return summary

        summary["start"] = df["timestamp"].min()
        summary["end"] = df["timestamp"].max()

        if "signal" in df.columns:
            signal_counts = (
                df["signal"]
                .value_counts()
                .to_dict()
            )

            summary["long_signals"] = int(
                signal_counts.get("LONG", 0)
            )

            summary["short_signals"] = int(
                signal_counts.get("SHORT", 0)
            )

            summary["no_signals"] = int(
                signal_counts.get("NO_SIGNAL", 0)
            )

        if "trend_regime" in df.columns:
            trend_counts = (
                df["trend_regime"]
                .value_counts()
                .to_dict()
            )

            summary["trending_up"] = int(
                trend_counts.get("TRENDING_UP", 0)
            )

            summary["trending_down"] = int(
                trend_counts.get("TRENDING_DOWN", 0)
            )

            summary["ranging"] = int(
                trend_counts.get("RANGING", 0)
            )

        if "volatility_regime" in df.columns:
            volatility_counts = (
                df["volatility_regime"]
                .value_counts()
                .to_dict()
            )

            summary["low_volatility"] = int(
                volatility_counts.get(
                    "LOW_VOLATILITY",
                    0
                )
            )

            summary["normal_volatility"] = int(
                volatility_counts.get(
                    "NORMAL_VOLATILITY",
                    0
                )
            )

            summary["high_volatility"] = int(
                volatility_counts.get(
                    "HIGH_VOLATILITY",
                    0
                )
            )

            summary["unknown_volatility"] = int(
                volatility_counts.get(
                    "UNKNOWN",
                    0
                )
            )

        return summary