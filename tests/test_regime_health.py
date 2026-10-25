from engines.regime_health import RegimeHealthMonitor


def create_trade(pnl, regime):
    return {
        "pnl": pnl,
        "trend_regime": regime,
    }


def main():

    monitor = RegimeHealthMonitor(
        minimum_trades=3,
        review_profit_factor=1.0,
        pause_profit_factor=0.80,
        review_win_rate=0.40,
        pause_win_rate=0.30,
    )

    trades = [
        create_trade(100, "TRENDING_UP"),
        create_trade(80, "TRENDING_UP"),
        create_trade(-40, "TRENDING_UP"),
        create_trade(90, "TRENDING_UP"),

        create_trade(-40, "RANGING"),
        create_trade(-30, "RANGING"),
        create_trade(10, "RANGING"),
        create_trade(-20, "RANGING"),

        create_trade(50, "TRENDING_DOWN"),
        create_trade(-20, "TRENDING_DOWN"),
    ]

    results = monitor.evaluate_all(trades)

    print("REGIME HEALTH TEST")
    print("==================")

    for regime, result in results.items():

        print(f"\nRegime: {regime}")
        print("Status:", result["status"])

        print("Metrics:")

        for key, value in result["metrics"].items():
            print(f"  {key}: {value}")

        print("Reasons:")

        for reason in result["reasons"]:
            print(" -", reason)

    print()

    trending_up_ok = (
        results["TRENDING_UP"]["status"] == "ACTIVE"
    )

    ranging_ok = (
        results["RANGING"]["status"] == "PAUSED"
    )

    trending_down_ok = (
        results["TRENDING_DOWN"]["status"]
        == "INSUFFICIENT_DATA"
    )

    if trending_up_ok and ranging_ok and trending_down_ok:
        print("REGIME HEALTH TEST PASSED")
    else:
        print("REGIME HEALTH TEST FAILED")


if __name__ == "__main__":
    main()