from engines.data_source import TestDataSource
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals


def main():

    source = TestDataSource()

    df = source.get_data(
        "XAUUSD",
        "1H"
    )

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
        trend_threshold=0.001,
    )

    result = generate_signals(df)

    print("Strategy engine test successful!")
    print()

    print(
        result[
            [
                "timestamp",
                "close",
                "rsi",
                "trend_regime",
                "volatility_regime",
                "signal",
                "signal_strength",
                "signal_reason",
            ]
        ]
    )


if __name__ == "__main__":
    main()