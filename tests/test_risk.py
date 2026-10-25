from engines.data_source import TestDataSource
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.risk import RiskEngine


def main():

    source = TestDataSource()

    df = source.get_data(
        "XAUUSD",
        "1H"
    )

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
        trend_threshold=0.001,
    )

    df = generate_signals(df)

    risk = RiskEngine(
        max_risk_per_trade=0.01,
        max_drawdown=0.10,
        max_daily_loss=0.03,
        max_position_value=1.0,
    )

    # Test the latest row.
    latest_signal = df.iloc[-1]["signal"]

    allowed, reasons = risk.check_signal(
        df=df,
        signal=latest_signal,
        account_balance=10000,
        peak_balance=10000,
        daily_pnl=0,
        starting_daily_balance=10000,
    )

    print("Risk engine test successful!")
    print()
    print(f"Latest signal: {latest_signal}")
    print(f"Trade allowed: {allowed}")
    print()

    print("Risk checks:")
    for reason in reasons:
        print(f"- {reason}")

    print()

    # Test position sizing.
    position_size = risk.calculate_position_size(
        account_balance=10000,
        entry_price=2670,
        stop_loss=2660,
    )

    print(
        f"Example calculated position size: "
        f"{position_size:.4f}"
    )

    print()

    # Test the kill switch.
    risk.activate_kill_switch()

    allowed, reasons = risk.check_signal(
        df=df,
        signal="LONG",
        account_balance=10000,
        peak_balance=10000,
        daily_pnl=0,
        starting_daily_balance=10000,
    )

    print("Kill-switch test:")
    print(f"Trade allowed: {allowed}")

    for reason in reasons:
        print(f"- {reason}")


if __name__ == "__main__":
    main()