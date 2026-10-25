import os
import tempfile

import pandas as pd

from engines.historical_pipeline import HistoricalPipeline


def create_test_csv(file_path):
    rows = []

    price = 2000.0

    for index in range(300):
        timestamp = (
            pd.Timestamp("2025-01-01")
            + pd.Timedelta(hours=index)
        )

        rows.append(
            {
                "Date": timestamp,
                "Open": price,
                "High": price + 8.0,
                "Low": price - 6.0,
                "Close": price + 2.0,
                "Volume": 1000,
            }
        )

        price += 1.0

    pd.DataFrame(rows).to_csv(
        file_path,
        index=False,
    )


def main():
    print(
        "\nStarting historical pipeline diagnostic..."
    )

    pipeline = HistoricalPipeline(
        minimum_rows=100
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        file_path = os.path.join(
            temp_dir,
            "xauusd_pipeline_test.csv",
        )

        create_test_csv(file_path)

        print(
            f"\nTest CSV created: {file_path}"
        )

        result = pipeline.run(file_path)

        df = result["data"]
        summary = result["summary"]

        print("\nPipeline output columns:")

        for column in df.columns:
            print(f"  {column}")

        print("\nPipeline summary:")

        print(
            f"  Rows              : "
            f"{summary['rows']}"
        )

        print(
            f"  Start             : "
            f"{summary['start']}"
        )

        print(
            f"  End               : "
            f"{summary['end']}"
        )

        print(
            f"  LONG signals      : "
            f"{summary['long_signals']}"
        )

        print(
            f"  SHORT signals     : "
            f"{summary['short_signals']}"
        )

        print(
            f"  NO_SIGNAL         : "
            f"{summary['no_signals']}"
        )

        print(
            f"  Trending up       : "
            f"{summary['trending_up']}"
        )

        print(
            f"  Trending down     : "
            f"{summary['trending_down']}"
        )

        print(
            f"  Ranging           : "
            f"{summary['ranging']}"
        )

        print(
            f"  Low volatility    : "
            f"{summary['low_volatility']}"
        )

        print(
            f"  Normal volatility : "
            f"{summary['normal_volatility']}"
        )

        print(
            f"  High volatility   : "
            f"{summary['high_volatility']}"
        )

        print(
            f"  Unknown volatility: "
            f"{summary['unknown_volatility']}"
        )

        print(
            "\nChecking required analysis columns..."
        )

        required_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "sma",
            "ema",
            "rsi",
            "atr",
            "trend_regime",
            "volatility_regime",
            "signal",
            "signal_strength",
            "signal_reason",
        ]

        for column in required_columns:
            assert column in df.columns, (
                f"Missing required column: {column}"
            )

        print(
            "  All required analysis columns exist."
        )

        print("\nChecking row count...")

        assert len(df) == 300

        print(
            "  300 analyzed rows confirmed."
        )

        print("\nChecking timestamps...")

        assert df[
            "timestamp"
        ].is_monotonic_increasing

        print(
            "  Timestamps are chronological."
        )

        print("\nChecking prices...")

        assert not df[
            ["open", "high", "low", "close"]
        ].isna().any().any()

        print(
            "  No missing OHLC prices."
        )

        print("\nChecking signal values...")

        allowed_signals = {
            "LONG",
            "SHORT",
            "NO_SIGNAL",
        }

        actual_signals = set(
            df["signal"].dropna().unique()
        )

        assert actual_signals.issubset(
            allowed_signals
        )

        print(
            "  Signal values are valid."
        )

    print(
        "\nHISTORICAL PIPELINE TEST PASSED"
    )


if __name__ == "__main__":
    main()