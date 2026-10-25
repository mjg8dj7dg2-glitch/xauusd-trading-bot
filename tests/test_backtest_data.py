import pandas as pd


def create_backtest_data():

    timestamps = pd.date_range(
        start="2026-01-05 09:00",
        periods=60,
        freq="h",
    )

    prices = [
        2650, 2652, 2654, 2656, 2658,
        2660, 2662, 2664, 2666, 2668,
        2670, 2672, 2674, 2676, 2678,
        2680, 2682, 2684, 2686, 2688,
        2690, 2692, 2694, 2696, 2698,
        2700, 2698, 2696, 2694, 2692,
        2690, 2688, 2686, 2684, 2682,
        2680, 2678, 2676, 2674, 2672,
        2670, 2672, 2674, 2676, 2678,
        2680, 2682, 2684, 2686, 2688,
        2690, 2692, 2694, 2696, 2698,
        2700, 2698, 2696, 2694, 2692,
        2690, 2688, 2686, 2684, 2682,
    ]

    data = []

    for timestamp, close in zip(
        timestamps,
        prices,
    ):

        data.append({
            "timestamp": timestamp,
            "open": close - 1,
            "high": close + 3,
            "low": close - 3,
            "close": close,
            "volume": 1000,
        })

    return pd.DataFrame(data)


if __name__ == "__main__":

    df = create_backtest_data()

    print("Backtest dataset created!")
    print()
    print(f"Candles: {len(df)}")
    print()
    print(df.head())
    print()
    print(df.tail())