from engines.health_report import HealthReport


def create_trade(pnl, regime):
    return {
        "pnl": pnl,
        "trend_regime": regime,
    }


def main():

    historical_trades = [
        create_trade(100, "TRENDING_UP"),
        create_trade(80, "TRENDING_UP"),
        create_trade(120, "TRENDING_UP"),
        create_trade(-50, "TRENDING_UP"),
        create_trade(90, "TRENDING_UP"),
        create_trade(70, "RANGING"),
        create_trade(-40, "RANGING"),
        create_trade(110, "TRENDING_DOWN"),
        create_trade(60, "TRENDING_DOWN"),
        create_trade(100, "TRENDING_UP"),
    ]

    recent_trades = [
        create_trade(30, "TRENDING_UP"),
        create_trade(-40, "RANGING"),
        create_trade(-35, "RANGING"),
        create_trade(20, "TRENDING_UP"),
        create_trade(-30, "RANGING"),
    ]

    all_trades = historical_trades + recent_trades

    report_engine = HealthReport(
        starting_balance=10000.0,
        minimum_recent_trades=5,
        minimum_regime_trades=3,
    )

    report = report_engine.build_report(
        historical_trades=historical_trades,
        recent_trades=recent_trades,
        all_trades=all_trades,
    )

    print("HEALTH REPORT TEST")
    print("==================")

    strategy_health = report["strategy_health"]

    print("\nOverall strategy health:")
    print("Status:", strategy_health["status"])

    print("\nReasons:")

    for reason in strategy_health["reasons"]:
        print("-", reason)

    print("\nRegime health:")

    for regime, result in report["regime_health"].items():

        print(f"\n{regime}")
        print("Status:", result["status"])

        for key, value in result["metrics"].items():
            print(f"{key}: {value}")

    print()

    if (
        "strategy_health" in report
        and "regime_health" in report
        and len(report["regime_health"]) > 0
    ):
        print("HEALTH REPORT TEST PASSED")
    else:
        print("HEALTH REPORT TEST FAILED")


if __name__ == "__main__":
    main()