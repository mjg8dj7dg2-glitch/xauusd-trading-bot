from engines.losing_patterns import (
    LosingPatternDetector,
)


def create_trade(
    direction,
    trend_regime,
    volatility_regime,
    rsi,
    atr,
    pnl,
):
    return {
        "direction": direction,
        "trend_regime": trend_regime,
        "volatility_regime": volatility_regime,
        "rsi": rsi,
        "atr": atr,
        "pnl": pnl,
    }


def main():

    trades = [

        create_trade(
            "LONG",
            "TRENDING_UP",
            "HIGH_VOLATILITY",
            68,
            4.0,
            -100,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "HIGH_VOLATILITY",
            72,
            4.5,
            -80,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "LOW_VOLATILITY",
            65,
            2.0,
            120,
        ),

        create_trade(
            "SHORT",
            "TRENDING_DOWN",
            "HIGH_VOLATILITY",
            45,
            4.2,
            -60,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "HIGH_VOLATILITY",
            70,
            4.1,
            -90,
        ),

        create_trade(
            "SHORT",
            "RANGING",
            "LOW_VOLATILITY",
            50,
            1.5,
            100,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "LOW_VOLATILITY",
            60,
            2.0,
            80,
        ),
    ]

    detector = LosingPatternDetector(
        minimum_losses=3,
        minimum_occurrences=2,
        minimum_percentage=0.50,
    )

    report = detector.analyze(
        trades
    )

    print("LOSING PATTERN TEST")
    print("===================")

    print(
        "\nTotal trades:",
        report["total_trades"],
    )

    print(
        "Losing trades:",
        report["losing_trades"],
    )

    print(
        "Loss rate:",
        f"{report['loss_rate']:.2%}",
    )

    print("\nPatterns:")

    for pattern in report["patterns"]:

        print(
            f"- {pattern['field']}: "
            f"{pattern['value']} "
            f"| occurrences: "
            f"{pattern['occurrences']} "
            f"| loss share: "
            f"{pattern['percentage_of_losses']:.2%}"
        )

    if (
        report["losing_trades"] == 4
        and len(report["patterns"]) > 0
    ):
        print(
            "\nLOSING PATTERN TEST PASSED"
        )

    else:
        print(
            "\nLOSING PATTERN TEST FAILED"
        )


if __name__ == "__main__":
    main()