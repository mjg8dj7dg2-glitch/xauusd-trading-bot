from engines.trade_memory import TradeMemory


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
            "LOW_VOLATILITY",
            66,
            2.3,
            2725,
            2725,
            180,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "LOW_VOLATILITY",
            63,
            2.5,
            2726,
            2725,
            120,
        ),

        create_trade(
            "LONG",
            "TRENDING_UP",
            "LOW_VOLATILITY",
            68,
            2.2,
            2724,
            2725,
            -40,
        ),

        create_trade(
            "SHORT",
            "TRENDING_DOWN",
            "HIGH_VOLATILITY",
            42,
            5.0,
            2710,
            2720,
            -100,
        ),

        create_trade(
            "LONG",
            "RANGING",
            "LOW_VOLATILITY",
            52,
            1.8,
            2720,
            2721,
            -60,
        ),
    ]

    current_trade = create_trade(
        "LONG",
        "TRENDING_UP",
        "LOW_VOLATILITY",
        67,
        2.4,
        2725,
        2725,
        0,
    )

    memory = TradeMemory(
        minimum_similarity=0.60,
        max_results=10,
    )

    report = memory.analyze(
        current_trade=current_trade,
        historical_trades=historical_trades,
    )

    print("TRADE MEMORY TEST")
    print("=================")

    print("\nSimilar trades:")

    for match in report["matches"]:

        print(
            f"Index: {match['index']} "
            f"| Similarity: "
            f"{match['similarity']:.2%} "
            f"| P&L: "
            f"{match['trade'].get('pnl')}"
        )

    print("\nSummary:")

    summary = report["summary"]

    for key, value in summary.items():

        print(
            f"{key}: {value}"
        )

    if (
        "matches" in report
        and "summary" in report
        and summary["similar_trades"] > 0
    ):
        print(
            "\nTRADE MEMORY TEST PASSED"
        )

    else:
        print(
            "\nTRADE MEMORY TEST FAILED"
        )


if __name__ == "__main__":
    main()