import os

from engines.historical_data import HistoricalDataLoader


DATA_FILE = os.path.join(
    "data",
    "xauusd",
    "raw",
    "XAUUSD_5m.csv",
)


def main():
    print("\nStarting real XAUUSD historical-data import test...")

    print(
        f"\nLooking for dataset:\n"
        f"  {os.path.abspath(DATA_FILE)}"
    )

    if not os.path.exists(DATA_FILE):
        print("\nERROR: XAUUSD CSV file was not found.")
        print(
            "\nExpected location:\n"
            f"  {os.path.abspath(DATA_FILE)}"
        )
        print(
            "\nMake sure the CSV is named exactly:"
            "\n  XAUUSD_5m.csv"
        )
        return

    loader = HistoricalDataLoader(
        minimum_rows=100
    )

    try:
        data = loader.load_csv(
            DATA_FILE
        )

    except Exception as exc:
        print(
            "\nERROR: Historical-data validation failed."
        )
        print(
            f"\nReason:\n  {exc}"
        )
        return

    summary = loader.summary(data)

    print(
        "\nHistorical XAUUSD data loaded successfully."
    )

    print(
        f"\nRows       : {summary['rows']}"
    )

    print(
        f"Start      : {summary['start']}"
    )

    print(
        f"End        : {summary['end']}"
    )

    print(
        f"Days       : {summary['days']}"
    )

    print(
        "\nColumns:"
    )

    for column in data.columns:
        print(
            f"  {column}"
        )

    print(
        "\nFirst 5 rows:"
    )

    print(
        data.head().to_string(
            index=False
        )
    )

    print(
        "\nLast 5 rows:"
    )

    print(
        data.tail().to_string(
            index=False
        )
    )

    print(
        "\nChecking OHLC data..."
    )

    assert not data[
        ["open", "high", "low", "close"]
    ].isnull().any().any()

    assert (
        data["high"] >= data["low"]
    ).all()

    assert (
        data["high"] >= data["open"]
    ).all()

    assert (
        data["high"] >= data["close"]
    ).all()

    assert (
        data["low"] <= data["open"]
    ).all()

    assert (
        data["low"] <= data["close"]
    ).all()

    print(
        "  OHLC validation passed."
    )

    print(
        "\nChecking timestamps..."
    )

    assert (
        data["timestamp"].is_monotonic_increasing
    )

    assert not data[
        "timestamp"
    ].duplicated().any()

    print(
        "  Timestamp validation passed."
    )

    print(
        "\nChecking required columns..."
    )

    required_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    ]

    for column in required_columns:
        assert column in data.columns, (
            f"Missing required column: {column}"
        )

    print(
        "  Required columns exist."
    )

    print(
        "\nREAL XAUUSD HISTORICAL-DATA "
        "IMPORT TEST PASSED"
    )


if __name__ == "__main__":
    main()