
import os
import tempfile

import pandas as pd

from engines.historical_data import (
    HistoricalDataError,
    HistoricalDataLoader,
)


def create_test_csv(
    file_path,
):
    rows = []

    price = 2000.0

    for index in range(150):
        timestamp = (
            pd.Timestamp("2025-01-01")
            + pd.Timedelta(
                hours=index
            )
        )

        open_price = price
        high_price = price + 5.0
        low_price = price - 4.0
        close_price = price + 1.0

        rows.append(
            {
                "Date": timestamp,
                "Open": open_price,
                "High": high_price,
                "Low": low_price,
                "Close": close_price,
                "Volume": 1000,
            }
        )

        price += 1.0

    pd.DataFrame(
        rows
    ).to_csv(
        file_path,
        index=False,
    )


def main():
    print(
        "\nStarting historical data loader diagnostic..."
    )

    loader = HistoricalDataLoader(
        minimum_rows=100
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        file_path = os.path.join(
            temp_dir,
            "xauusd_test.csv",
        )

        create_test_csv(
            file_path
        )

        print(
            f"\nTest CSV created: {file_path}"
        )

        df = loader.load_csv(
            file_path
        )

        print(
            "\nLoaded columns:"
        )

        for column in df.columns:
            print(
                f"  {column}"
            )

        summary = loader.summary(
            df
        )

        print(
            "\nHistorical data summary:"
        )

        print(
            f"  Rows       : {summary['rows']}"
        )

        print(
            f"  Start      : {summary['start']}"
        )

        print(
            f"  End        : {summary['end']}"
        )

        print(
            f"  Days       : {summary['days']}"
        )

        assert len(df) == 150

        assert list(
            df[
                [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                ]
            ].columns
        ) == [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        ]

        assert (
            df["timestamp"]
            .is_monotonic_increasing
        )

        assert (
            not df[
                [
                    "open",
                    "high",
                    "low",
                    "close",
                ]
            ]
            .isna()
            .any()
            .any()
        )

        print(
            "\nTesting invalid data..."
        )

        invalid = df.copy()

        invalid.loc[
            10,
            "high"
        ] = 1000.0

        invalid.loc[
            10,
            "low"
        ] = 2000.0

        try:
            loader.validate(
                invalid
            )

            raise AssertionError(
                "Invalid data was not rejected."
            )

        except HistoricalDataError:
            print(
                "  Invalid candle correctly rejected."
            )

    print(
        "\nHISTORICAL DATA TEST PASSED"
    )


if __name__ == "__main__":
    main()
