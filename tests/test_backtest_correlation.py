from engines.backtest import BacktestEngine
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from tests.test_strategy_controlled import create_controlled_data


def prepare_data():
    df = create_controlled_data()

    df = add_technical_features(
        df,
        sma_period=3,
        ema_period=3,
        rsi_period=5,
        atr_period=5,
    )

    df = add_market_regime(
        df,
        volatility_period=5,
        fast_period=3,
        slow_period=6,
        trend_threshold=0.0002,
    )

    df = generate_signals(df)

    return df


def create_comparison_market(df):
    """
    Create a synthetic comparison market.

    Its prices are scaled versions of the primary market,
    so its returns are almost perfectly correlated.

    This is only for testing the correlation-risk logic.
    """

    comparison = df[["timestamp", "close"]].copy()

    comparison["close"] = comparison["close"] * 1.01

    return comparison


def main():
    df = prepare_data()

    signal_count = df["signal"].isin(["LONG", "SHORT"]).sum()

    print("Strategy signals generated:", signal_count)

    comparison_data = create_comparison_market(df)

    backtest = BacktestEngine(
        initial_balance=10000,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,

        # Enable comparison-market correlation checking.
        comparison_data=comparison_data,

        # The controlled test produces its signal early.
        # A smaller window lets the test calculate correlation
        # at the time of that signal.
        correlation_window=10,

        # Block trades when absolute correlation reaches 0.80.
        maximum_absolute_correlation=0.80,
    )

    stats = backtest.run(df)

    print("\nBacktest with high correlation:\n")

    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\nRisk events:")

    for event in backtest.risk_events:
        print(event)

    print()

    correlation_block_found = False

    for event in backtest.risk_events:
        for reason in event.get("reasons", []):
            if "Correlation risk" in reason:
                correlation_block_found = True

    if stats["total_trades"] == 0 and correlation_block_found:
        print("CORRELATION RISK TEST PASSED")
    else:
        print("CORRELATION RISK TEST FAILED")


if __name__ == "__main__":
    main()