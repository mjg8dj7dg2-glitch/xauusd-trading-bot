import os

from engines.pipeline import TradingPipeline


DATA_FILE = os.path.join(
    "data",
    "xauusd",
    "raw",
    "XAUUSD_5m.csv",
)


def main():
    print("\nStarting REAL XAUUSD pipeline diagnostic...")

    print(
        f"\nDataset:\n"
        f"  {os.path.abspath(DATA_FILE)}"
    )

    if not os.path.exists(DATA_FILE):
        print("\nERROR: XAUUSD dataset was not found.")
        return

    pipeline = TradingPipeline(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        minimum_rows=100,
    )

    print(
        "\nRunning real XAUUSD data through "
        "the complete analysis pipeline..."
    )

    result = pipeline.run(
        file_path=DATA_FILE
    )

    data = result["data"]
    analysis = result["analysis"]

    print(
        "\nREAL XAUUSD ANALYSIS COMPLETED"
    )

    print(
        f"\nRows analyzed       : {len(data)}"
    )

    print(
        f"Start               : {data['timestamp'].min()}"
    )

    print(
        f"End                 : {data['timestamp'].max()}"
    )

    print(
        "\nSignal counts:"
    )

    signal_counts = (
        data["signal"]
        .value_counts()
    )

    for signal, count in signal_counts.items():
        print(
            f"  {signal:<15}: {count}"
        )

    print(
        "\nTrend regimes:"
    )

    trend_counts = (
        data["trend_regime"]
        .value_counts()
    )

    for regime, count in trend_counts.items():
        print(
            f"  {regime:<20}: {count}"
        )

    print(
        "\nVolatility regimes:"
    )

    volatility_counts = (
        data["volatility_regime"]
        .value_counts()
    )

    for regime, count in volatility_counts.items():
        print(
            f"  {regime:<20}: {count}"
        )

    print(
        "\nSignal percentages:"
    )

    total_rows = len(data)

    for signal in [
        "LONG",
        "SHORT",
        "NO_SIGNAL",
    ]:
        count = int(
            signal_counts.get(
                signal,
                0,
            )
        )

        percentage = (
            count / total_rows * 100
            if total_rows > 0
            else 0.0
        )

        print(
            f"  {signal:<15}: "
            f"{count:>6} "
            f"({percentage:.2f}%)"
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
        "returns",
        "volatility",
        "volatility_regime",
        "trend_regime",
        "signal",
        "signal_strength",
        "signal_reason",
    ]

    for column in required_columns:
        assert column in data.columns, (
            f"Missing required column: {column}"
        )

    print(
        "  All required analysis columns exist."
    )

    print(
        "\nChecking indicator data..."
    )

    indicator_columns = [
        "sma",
        "ema",
        "rsi",
        "atr",
        "volatility",
    ]

    for column in indicator_columns:
        valid_values = data[column].notna().sum()

        print(
            f"  {column:<15}: "
            f"{valid_values} valid values"
        )

        assert valid_values > 0, (
            f"No valid values found for {column}"
        )

    print(
        "\nChecking signal values..."
    )

    valid_signals = {
        "LONG",
        "SHORT",
        "NO_SIGNAL",
    }

    actual_signals = set(
        data["signal"]
        .dropna()
        .unique()
    )

    assert actual_signals.issubset(
        valid_signals
    ), (
        f"Unexpected signal values: "
        f"{actual_signals - valid_signals}"
    )

    print(
        "  Signal values are valid."
    )

    print(
        "\nChecking timestamps..."
    )

    assert (
        data["timestamp"]
        .is_monotonic_increasing
    )

    assert not data[
        "timestamp"
    ].duplicated().any()

    print(
        "  Timestamps are chronological "
        "and unique."
    )

    print(
        "\nChecking prices..."
    )

    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    assert not data[
        price_columns
    ].isnull().any().any()

    assert (
        data[price_columns] > 0
    ).all().all()

    print(
        "  Price data is valid."
    )

    print(
        "\nPipeline analysis summary:"
    )

    if isinstance(analysis, dict):
        for key, value in analysis.items():
            print(
                f"  {key}: {value}"
            )

    print(
        "\nREAL XAUUSD PIPELINE TEST PASSED"
    )


if __name__ == "__main__":
    main()