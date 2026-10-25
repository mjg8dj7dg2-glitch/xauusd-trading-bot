from engines.backtest import BacktestEngine
from engines.risk import RiskEngine
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


def main():

    df = prepare_data()

    signal_count = (
        df["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    print("Strategy signals generated:", signal_count)

    # Create a risk engine and activate its kill switch.
    risk_engine = RiskEngine()
    risk_engine.activate_kill_switch()

    backtest = BacktestEngine(
        initial_balance=10000,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        risk_engine=risk_engine,
    )

    stats = backtest.run(df)

    print()
    print("Backtest with kill switch:")
    print()

    for key, value in stats.items():
        print(f"{key}: {value}")

    print()
    print("Risk events:")

    for event in backtest.risk_events:
        print(event)

    print()

    if stats["total_trades"] == 0:
        print("KILL SWITCH TEST PASSED")
    else:
        print("KILL SWITCH TEST FAILED")


if __name__ == "__main__":
    main()