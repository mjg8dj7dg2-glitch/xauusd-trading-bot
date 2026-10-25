from engines.strategy_health import StrategyHealthMonitor


def create_trade(pnl):
    return {
        "pnl": pnl
    }


def main():

    monitor = StrategyHealthMonitor(
        minimum_trades=5,
        review_profit_factor=1.0,
        pause_profit_factor=0.80,
        review_win_rate_drop=0.10,
        pause_win_rate_drop=0.20,
        review_drawdown=0.10,
        pause_drawdown=0.15,
    )

    historical_trades = [
        create_trade(100),
        create_trade(80),
        create_trade(120),
        create_trade(-50),
        create_trade(90),
        create_trade(70),
        create_trade(-40),
        create_trade(110),
        create_trade(60),
        create_trade(100),
    ]

    recent_trades = [
        create_trade(30),
        create_trade(-40),
        create_trade(-35),
        create_trade(20),
        create_trade(-30),
    ]

    result = monitor.evaluate(
        historical_trades=historical_trades,
        recent_trades=recent_trades,
    )

    print("STRATEGY HEALTH TEST")
    print("====================")

    print("\nStatus:")
    print(result["status"])

    print("\nHistorical metrics:")
    for key, value in result["historical"].items():
        print(f"{key}: {value}")

    print("\nRecent metrics:")
    for key, value in result["recent"].items():
        print(f"{key}: {value}")

    print("\nWin-rate change:")
    print(result["win_rate_change"])

    print("\nProfit-factor change:")
    print(result["profit_factor_change"])

    print("\nReasons:")

    for reason in result["reasons"]:
        print("-", reason)

    print()

    if result["status"] in ["REVIEW", "PAUSED"]:
        print("STRATEGY HEALTH TEST PASSED")
    else:
        print("STRATEGY HEALTH TEST FAILED")


if __name__ == "__main__":
    main()