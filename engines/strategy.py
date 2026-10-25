import pandas as pd


def generate_signals(df):
    """
    Generate basic trend-following signals.

    LONG:
        EMA > SMA
        RSI between 50 and 70
        TRENDING_UP
        Volatility is not HIGH

    SHORT:
        EMA < SMA
        RSI between 30 and 50
        TRENDING_DOWN
        Volatility is not HIGH
    """

    result = df.copy()

    result["signal"] = "NO_SIGNAL"
    result["signal_strength"] = 0.0
    result["signal_reason"] = ""

    long_condition = (
        (result["ema"] > result["sma"])
        & (result["rsi"] >= 50)
        & (result["rsi"] <= 70)
        & (result["trend_regime"] == "TRENDING_UP")
        & (result["volatility_regime"] != "HIGH_VOLATILITY")
    )

    short_condition = (
        (result["ema"] < result["sma"])
        & (result["rsi"] >= 30)
        & (result["rsi"] <= 50)
        & (result["trend_regime"] == "TRENDING_DOWN")
        & (result["volatility_regime"] != "HIGH_VOLATILITY")
    )

    result.loc[
        long_condition,
        "signal"
    ] = "LONG"

    result.loc[
        short_condition,
        "signal"
    ] = "SHORT"

    result.loc[
        long_condition,
        "signal_strength"
    ] = 1.0

    result.loc[
        short_condition,
        "signal_strength"
    ] = 1.0

    result.loc[
        long_condition,
        "signal_reason"
    ] = "Trend up + EMA above SMA + RSI confirms"

    result.loc[
        short_condition,
        "signal_reason"
    ] = "Trend down + EMA below SMA + RSI confirms"

    return result