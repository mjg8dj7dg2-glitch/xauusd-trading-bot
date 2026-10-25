import pandas as pd

from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals


def create_controlled_data():

    timestamps = pd.date_range(
        start="2026-01-01 00:00",
        periods=60,
        freq="h",
    )

    prices = [
        # Initial movement
        2700, 2701, 2702, 2703, 2702,
        2704, 2705, 2706, 2705, 2707,

        # Uptrend with pullbacks
        2708, 2709, 2710, 2709, 2711,
        2712, 2713, 2712, 2714, 2715,
        2716, 2715, 2717, 2718, 2719,
        2718, 2720, 2721, 2722, 2721,
        2723, 2724, 2725, 2724, 2726,

        # More consolidation/pullback
        2725, 2724, 2723, 2724, 2725,
        2726, 2727, 2726, 2728, 2729,

        # Continued movement
        2730, 2731, 2730, 2732, 2733,
        2734, 2733, 2735, 2736, 2737,

        # Final pullback
        2736, 2735, 2734, 2735, 2736,
        2737, 2738, 2737, 2739, 2740,
    ]

    data = []

    for timestamp, close in zip(timestamps, prices):

        data.append(
            {
                "timestamp": timestamp,
                "open": close - 0.5,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": 1000,
            }
        )

    return pd.DataFrame(data)


def main():

    df = create_controlled_data()

    df = add_technical_features(
        df,
        sma_period=3,
        ema_period=3,
        rsi_period=5,
        atr_period=5,
    )

    df = add_market_regime(
        df,
        volatility_period=5,
        fast_period=3,
        slow_period=6,
        trend_threshold=0.0002,
    )

    df = generate_signals(df)

    print("Controlled strategy test")
    print()

    print(
        df[
            [
                "timestamp",
                "close",
                "ema",
                "sma",
                "rsi",
                "trend_regime",
                "volatility_regime",
                "signal",
                "signal_reason",
            ]
        ].tail(25)
    )

    print()

    signal_count = (
        df["signal"] != "NO_SIGNAL"
    ).sum()

    print("Signals generated:", signal_count)

    if signal_count > 0:
        print("CONTROLLED STRATEGY TEST PASSED")
    else:
        print("CONTROLLED STRATEGY TEST FAILED")


if __name__ == "__main__":
    main()