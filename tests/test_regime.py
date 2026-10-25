from engines.data_source import TestDataSource
from engines.regime import add_market_regime


def main():

    source = TestDataSource()

    df = source.get_data(
        "XAUUSD",
        "1H"
    )

    result = add_market_regime(
        df,
        volatility_period=5,
        fast_period=3,
        slow_period=6,
        trend_threshold=0.001,
    )

    print("Market-regime test successful!")
    print()

    print(
        result[
            [
                "timestamp",
                "close",
                "volatility",
                "volatility_regime",
                "trend_regime",
            ]
        ]
    )


if __name__ == "__main__":
    main()