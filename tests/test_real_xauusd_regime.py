import os

import pandas as pd

from engines.pipeline import TradingPipeline


DATA_FILE = os.path.join(
    "data",
    "xauusd",
    "raw",
    "XAUUSD_5m.csv",
)


def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_distribution(data, column):
    print(f"\n{column} distribution:")

    counts = (
        data[column]
        .value_counts(dropna=False)
        .sort_index()
    )

    total = len(data)

    for value, count in counts.items():
        percentage = (
            count / total * 100
            if total > 0
            else 0.0
        )

        print(
            f"  {str(value):<25} "
            f"{count:>8} "
            f"({percentage:>6.2f}%)"
        )


def main():
    print_section(
        "REAL XAUUSD REGIME DIAGNOSTIC"
    )

    print(
        f"\nDataset:\n"
        f"  {os.path.abspath(DATA_FILE)}"
    )

    if not os.path.exists(DATA_FILE):
        print(
            "\nERROR: XAUUSD dataset was not found."
        )
        return

    pipeline = TradingPipeline(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        minimum_rows=100,
    )

    print(
        "\nRunning analysis..."
    )

    result = pipeline.run(
        file_path=DATA_FILE
    )

    data = result["data"]

    print_section(
        "DATASET SUMMARY"
    )

    print(
        f"Rows        : {len(data)}"
    )

    print(
        f"Start       : {data['timestamp'].min()}"
    )

    print(
        f"End         : {data['timestamp'].max()}"
    )

    print_section(
        "VOLATILITY DISTRIBUTION"
    )

    print_distribution(
        data,
        "volatility_regime",
    )

    print_section(
        "RAW VOLATILITY STATISTICS"
    )

    volatility = (
        pd.to_numeric(
            data["volatility"],
            errors="coerce",
        )
        .dropna()
    )

    print(
        f"Count       : {len(volatility)}"
    )

    print(
        f"Minimum     : {volatility.min():.8f}"
    )

    print(
        f"25th pct    : {volatility.quantile(0.25):.8f}"
    )

    print(
        f"Median      : {volatility.median():.8f}"
    )

    print(
        f"75th pct    : {volatility.quantile(0.75):.8f}"
    )

    print(
        f"90th pct    : {volatility.quantile(0.90):.8f}"
    )

    print(
        f"95th pct    : {volatility.quantile(0.95):.8f}"
    )

    print(
        f"99th pct    : {volatility.quantile(0.99):.8f}"
    )

    print(
        f"Maximum     : {volatility.max():.8f}"
    )

    print_section(
        "ATR STATISTICS"
    )

    atr = (
        pd.to_numeric(
            data["atr"],
            errors="coerce",
        )
        .dropna()
    )

    print(
        f"Count       : {len(atr)}"
    )

    print(
        f"Minimum     : {atr.min():.6f}"
    )

    print(
        f"25th pct    : {atr.quantile(0.25):.6f}"
    )

    print(
        f"Median      : {atr.median():.6f}"
    )

    print(
        f"75th pct    : {atr.quantile(0.75):.6f}"
    )

    print(
        f"90th pct    : {atr.quantile(0.90):.6f}"
    )

    print(
        f"95th pct    : {atr.quantile(0.95):.6f}"
    )

    print(
        f"99th pct    : {atr.quantile(0.99):.6f}"
    )

    print(
        f"Maximum     : {atr.max():.6f}"
    )

    print_section(
        "TREND REGIME DISTRIBUTION"
    )

    print_distribution(
        data,
        "trend_regime",
    )

    print_section(
        "SIGNAL DISTRIBUTION"
    )

    print_distribution(
        data,
        "signal",
    )

    print_section(
        "SIGNALS BY TREND REGIME"
    )

    signal_by_trend = pd.crosstab(
        data["trend_regime"],
        data["signal"],
    )

    print(
        signal_by_trend.to_string()
    )

    print_section(
        "SIGNALS BY VOLATILITY REGIME"
    )

    signal_by_volatility = pd.crosstab(
        data["volatility_regime"],
        data["signal"],
    )

    print(
        signal_by_volatility.to_string()
    )

    print_section(
        "RSI STATISTICS"
    )

    rsi = (
        pd.to_numeric(
            data["rsi"],
            errors="coerce",
        )
        .dropna()
    )

    print(
        f"Minimum     : {rsi.min():.4f}"
    )

    print(
        f"25th pct    : {rsi.quantile(0.25):.4f}"
    )

    print(
        f"Median      : {rsi.median():.4f}"
    )

    print(
        f"75th pct    : {rsi.quantile(0.75):.4f}"
    )

    print(
        f"Maximum     : {rsi.max():.4f}"
    )

    print_section(
        "SIGNAL RSI STATISTICS"
    )

    signal_rows = data[
        data["signal"].isin(
            ["LONG", "SHORT"]
        )
    ].copy()

    if signal_rows.empty:
        print(
            "No LONG or SHORT signals found."
        )
    else:
        signal_rsi = (
            pd.to_numeric(
                signal_rows["rsi"],
                errors="coerce",
            )
            .dropna()
        )

        print(
            f"Signal count: {len(signal_rows)}"
        )

        print(
            f"Minimum     : {signal_rsi.min():.4f}"
        )

        print(
            f"Median      : {signal_rsi.median():.4f}"
        )

        print(
            f"Maximum     : {signal_rsi.max():.4f}"
        )

    print_section(
        "SIGNAL SPACING"
    )

    signal_timestamps = (
        data.loc[
            data["signal"].isin(
                ["LONG", "SHORT"]
            ),
            "timestamp",
        ]
        .sort_values()
    )

    if len(signal_timestamps) < 2:
        print(
            "Not enough signals to calculate spacing."
        )
    else:
        spacing = (
            signal_timestamps
            .diff()
            .dropna()
            .dt.total_seconds()
            / 60.0
        )

        print(
            f"Minimum gap  : "
            f"{spacing.min():.1f} minutes"
        )

        print(
            f"Median gap   : "
            f"{spacing.median():.1f} minutes"
        )

        print(
            f"Average gap  : "
            f"{spacing.mean():.1f} minutes"
        )

    print_section(
        "REGIME DIAGNOSTIC"
    )

    low_count = int(
        (
            data["volatility_regime"]
            == "LOW_VOLATILITY"
        ).sum()
    )

    normal_count = int(
        (
            data["volatility_regime"]
            == "NORMAL_VOLATILITY"
        ).sum()
    )

    high_count = int(
        (
            data["volatility_regime"]
            == "HIGH_VOLATILITY"
        ).sum()
    )

    unknown_count = int(
        (
            data["volatility_regime"]
            == "UNKNOWN"
        ).sum()
    )

    total = len(data)

    print(
        f"Low volatility       : {low_count}"
    )

    print(
        f"Normal volatility    : {normal_count}"
    )

    print(
        f"High volatility      : {high_count}"
    )

    print(
        f"Unknown volatility   : {unknown_count}"
    )

    if total > 0:
        print(
            "\nLow-volatility percentage:"
        )

        print(
            f"  {low_count / total * 100:.2f}%"
        )

    print_section(
        "DIAGNOSTIC CONCLUSION"
    )

    print(
        "This test does NOT modify any strategy "
        "parameters."
    )

    print(
        "It only measures how the current "
        "regime engine behaves on real XAUUSD data."
    )

    print(
        "\nREAL XAUUSD REGIME DIAGNOSTIC PASSED"
    )


if __name__ == "__main__":
    main()