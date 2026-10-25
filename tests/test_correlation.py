import pandas as pd

from engines.correlation import (
    calculate_correlation,
    classify_correlation,
    check_correlation_risk,
)


def create_test_data():

    timestamps = pd.date_range(
        start="2026-01-05 09:00",
        periods=30,
        freq="h",
    )

    primary_prices = [
        100, 101, 102, 103, 104,
        105, 106, 107, 108, 109,
        110, 109, 111, 112, 113,
        114, 115, 116, 117, 118,
        119, 120, 121, 120, 122,
        123, 124, 125, 126, 127,
    ]

    comparison_prices = [
        200, 202, 204, 206, 208,
        210, 212, 214, 216, 218,
        220, 218, 222, 224, 226,
        228, 230, 232, 234, 236,
        238, 240, 242, 240, 244,
        246, 248, 250, 252, 254,
    ]

    primary = pd.DataFrame({
        "timestamp": timestamps,
        "close": primary_prices,
    })

    comparison = pd.DataFrame({
        "timestamp": timestamps,
        "close": comparison_prices,
    })

    return primary, comparison


def main():

    primary, comparison = create_test_data()

    result = calculate_correlation(
        primary,
        comparison,
        window=10,
    )

    latest_correlation = (
        result.iloc[-1]["correlation"]
    )

    classification = classify_correlation(
        latest_correlation
    )

    allowed, message = check_correlation_risk(
        latest_correlation
    )

    print("Correlation engine test successful!")
    print()

    print(
        f"Latest correlation: "
        f"{latest_correlation:.4f}"
    )

    print(
        f"Classification: "
        f"{classification}"
    )

    print(
        f"Risk allowed: "
        f"{allowed}"
    )

    print(
        f"Risk message: "
        f"{message}"
    )

    print()
    print("Recent correlation values:")

    print(
        result[
            [
                "timestamp",
                "correlation",
            ]
        ].tail(5)
    )


if __name__ == "__main__":
    main()