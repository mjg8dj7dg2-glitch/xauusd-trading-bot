from engines.data_source import get_data_source


def main():

    source = get_data_source("test")

    data = source.get_data(
        instrument="XAUUSD",
        timeframe="1H"
    )

    print("Data-source test successful!")
    print(f"Candles received: {len(data)}")
    print()
    print(data)


if __name__ == "__main__":
    main()