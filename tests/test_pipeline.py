import pandas as pd
import numpy as np

from engines.pipeline import TradingPipeline


def create_test_data(rows=300):
    timestamps = pd.date_range(
        "2026-01-01",
        periods=rows,
        freq="h",
    )

    close_prices = []

    price = 2700.0

    for i in range(rows):

        if i < 100:
            movement = 2.5
        elif i < 200:
            movement = -2.5
        else:
            movement = 2.5

        noise = np.sin(i / 3.0) * 0.25

        price += movement + noise

        close_prices.append(price)

    close = np.array(close_prices)

    open_prices = close - 0.4
    high = close + 1.2
    low = close - 1.2
    volume = np.full(rows, 1000)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_prices,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def print_signal_summary(data):
    print()
    print("=" * 70)
    print("SIGNAL DIAGNOSTIC")
    print("=" * 70)

    signal_counts = data["signal"].value_counts()

    print()
    print("Signal counts:")

    for signal, count in signal_counts.items():
        print(f"  {signal}: {count}")

    print()

    print("Trend regimes:")

    regime_counts = data[
        "trend_regime"
    ].value_counts()

    for regime, count in regime_counts.items():
        print(f"  {regime}: {count}")

    print()

    print("Volatility regimes:")

    volatility_counts = data[
        "volatility_regime"
    ].value_counts()

    for regime, count in volatility_counts.items():
        print(f"  {regime}: {count}")

    print("=" * 70)


def print_backtest_structure(backtest):
    print()
    print("=" * 70)
    print("BACKTEST STRUCTURE DIAGNOSTIC")
    print("=" * 70)

    print()
    print("Backtest result keys:")

    for key in backtest.keys():
        value = backtest[key]

        if isinstance(value, list):
            print(
                f"  {key}: list "
                f"({len(value)} items)"
            )
        elif isinstance(value, dict):
            print(
                f"  {key}: dict "
                f"({len(value)} items)"
            )
        else:
            print(
                f"  {key}: "
                f"{type(value).__name__}"
            )

    trades = backtest.get(
        "trades",
        [],
    )

    print()
    print(
        f"Completed trades: {len(trades)}"
    )

    if trades:

        print()
        print("First completed trade:")

        print("-" * 70)

        first_trade = trades[0]

        for key, value in first_trade.items():
            print(
                f"{key}: {value}"
            )

        print("-" * 70)

    risk_events = backtest.get(
        "risk_events",
        None,
    )

    print()

    if risk_events is None:
        print(
            "risk_events key: NOT PRESENT"
        )
    else:
        print(
            f"risk_events count: "
            f"{len(risk_events)}"
        )

        if risk_events:
            print()
            print("First risk event:")

            print("-" * 70)

            for key, value in risk_events[0].items():
                print(
                    f"{key}: {value}"
                )

            print("-" * 70)

    print()
    print("=" * 70)


def main():

    print()
    print(
        "Starting integrated pipeline diagnostic..."
    )
    print()

    df = create_test_data()

    print(
        f"Test candles created: {len(df)}"
    )

    pipeline = TradingPipeline(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        commission_per_trade=0.0,
        slippage_per_trade=0.0,
        maximum_absolute_correlation=0.80,
        minimum_recent_trades=5,
        minimum_regime_trades=3,
    )

    print(
        "Running analysis..."
    )

    analyzed_data = pipeline.run_analysis(
        df
    )

    print_signal_summary(
        analyzed_data
    )

    print()
    print(
        "Running complete backtest..."
    )

    report = pipeline.run(df)

    print_backtest_structure(
        report["backtest"]
    )

    pipeline.print_report(
        report
    )

    print()
    print("=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()