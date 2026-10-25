from engines.memory_report import MemoryReport


def create_trade(
    direction,
    trend_regime,
    volatility_regime,
    rsi,
    atr,
    ema,
    sma,
    pnl,
):
    return {
        "direction": direction,
        "trend_regime": trend_regime,
        "volatility_regime": volatility_regime,
        "rsi": rsi,
        "atr": atr,
        "ema": ema,
        "sma": sma,
        "pnl": pnl,
    }


def main():

    historical_trades = [

        create_trade(
            "LONG",
            "TRENDING_UP",
            "HIGH_VOLATILITY",
            68,
            4.0,
            2730,
            2725,
            -100,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "HIGH_VOLATILITY",
            72,
            4.5,
            2731,
            2726,
            -80,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "LOW_VOLATILITY",
            65,
            2.0,
            2728,
            2725,
            120,
        ),

        create_trade(
            "SHORT",
            "TRENDING_DOWN",
            "HIGH_VOLATILITY",
            45,
            4.2,
            2715,
            2720,
            -60,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "HIGH_VOLATILITY",
            70,
            4.1,
            2732,
            2727,
            -90,
        ),

        create_trade(
            "SHORT",
            "RANGING",
            "LOW_VOLATILITY",
            50,
            1.5,
            2720,
            2721,
            100,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "LOW_VOLATILITY",
            60,
            2.0,
            2727,
            2725,
            80,
        ),
    ]

    current_trade = {
        "direction": "LONG",
        "trend_regime": "TRENDING_UP",
        "volatility_regime": "HIGH_VOLATILITY",
        "rsi": 69,
        "atr": 4.1,
        "ema": 2731,
        "sma": 2726,
    }

    memory = MemoryReport(
        minimum_similarity=0.60,
        max_similar_trades=5,
        minimum_losses=3,
        minimum_occurrences=2,
        minimum_percentage=0.50,
    )

    report = memory.build_report(
        current_trade=current_trade,
        historical_trades=historical_trades,
        recent_count=5,
    )

    summary = memory.summarize(report)

    print("MEMORY REPORT TEST")
    print("==================")

    print("\nSimilar trades:")
    print(
        "Count:",
        summary["similar_trade_count"],
    )

    print(
        "Win rate:",
        f"{summary['similar_trade_win_rate']:.2%}",
    )

    print(
        "Average P&L:",
        summary["similar_trade_average_pnl"],
    )

    print("\nLosing patterns:")
    print(
        "Total patterns:",
        summary["losing_pattern_count"],
    )

    for pattern in report[
        "losing_patterns"
    ]["patterns"]:

        print(
            f"- {pattern['field']}: "
            f"{pattern['value']} "
            f"| occurrences: "
            f"{pattern['occurrences']}"
        )

    print("\nRecent losing patterns:")
    print(
        "Patterns:",
        summary[
            "recent_losing_pattern_count"
        ],
    )

    print(
        "\nMEMORY REPORT TEST PASSED"
    )


if __name__ == "__main__":
    main()