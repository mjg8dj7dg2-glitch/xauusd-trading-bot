import pandas as pd


def add_breakout_signals(df):
    """
    Add close-confirmed breakout signals using previously known levels.

    breakout_signal:
         1 = bullish breakout
        -1 = bearish breakout
         0 = no breakout

    A level is shifted by one row to prevent using a level first
    exposed on the current candle. The input DataFrame is not modified.
    """
    required = ["close", "swing_high_price", "swing_low_price"]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    result = df.copy()

    close = pd.to_numeric(result["close"], errors="raise")
    resistance = pd.to_numeric(
        result["swing_high_price"], errors="raise"
    ).shift(1)
    support = pd.to_numeric(
        result["swing_low_price"], errors="raise"
    ).shift(1)

    previous_close = close.shift(1)

    bullish = (
        resistance.notna()
        & previous_close.notna()
        & (close > resistance)
        & (previous_close <= resistance)
    )

    bearish = (
        support.notna()
        & previous_close.notna()
        & (close < support)
        & (previous_close >= support)
    )

    result["breakout_signal"] = 0
    result.loc[bullish, "breakout_signal"] = 1
    result.loc[bearish, "breakout_signal"] = -1

    return result
