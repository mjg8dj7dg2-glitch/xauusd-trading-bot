from engines.data_source import TestDataSource
from engines.technical import add_technical_features


def main():

    source = TestDataSource()

    df = source.get_data(
        "XAUUSD",
        "1H"
    )

    result = add_technical_features(
        df,
        sma_period=3,
        ema_period=3,
        rsi_period=5,
        atr_period=5,
    )

    print("Technical analysis test successful!")
    print()

    print(
        result[
            [
                "timestamp",
                "close",
                "sma",
                "ema",
                "rsi",
                "atr",
                "returns",
            ]
        ]
    )


if __name__ == "__main__":
    main()