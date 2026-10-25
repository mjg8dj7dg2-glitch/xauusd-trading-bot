from engines.backtest import BacktestEngine
from engines.news import create_news_event
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

    # Put a high-impact CPI event 20 minutes
    # after the strategy signal.
    news_event = create_news_event(
        event_time="2026-01-02 11:20",
        event_name="CPI",
        currency="USD",
        impact="HIGH",
    )

    backtest = BacktestEngine(
        initial_balance=10000,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        news_events=[news_event],
        news_before_minutes=30,
        news_after_minutes=15,
    )

    stats = backtest.run(df)

    print()
    print("Backtest with high-impact news:")
    print()

    for key, value in stats.items():
        print(f"{key}: {value}")

    print()
    print("Risk events:")

    for event in backtest.risk_events:
        print(event)

    print()

    if stats["total_trades"] == 0:
        print("NEWS RISK TEST PASSED")
    else:
        print("NEWS RISK TEST FAILED")


if __name__ == "__main__":
    main()