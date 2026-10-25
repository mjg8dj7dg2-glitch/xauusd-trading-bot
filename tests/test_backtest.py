from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.backtest import BacktestEngine

from tests.test_strategy_controlled import create_controlled_data


def main():

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

    signal_count = (
        df["signal"] != "NO_SIGNAL"
    ).sum()

    print("Strategy signals generated:", signal_count)
    print()

    engine = BacktestEngine(
        initial_balance=10000,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
    )

    statistics = engine.run(df)

    print("Backtest completed!")
    print()

    for key, value in statistics.items():

        if isinstance(value, float):

            if "rate" in key or "drawdown" in key:
                print(f"{key}: {value:.2%}")

            else:
                print(f"{key}: {value:.2f}")

        else:
            print(f"{key}: {value}")

    print()
    print("Simulated trades:")

    for trade in engine.trades:
        print(trade)


if __name__ == "__main__":
    main()