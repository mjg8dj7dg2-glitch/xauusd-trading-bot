import pandas as pd


def calculate_sma(df, period=20):
    """Calculate Simple Moving Average."""
    return df["close"].rolling(
        window=period,
        min_periods=period
    ).mean()


def calculate_ema(df, period=20):
    """Calculate Exponential Moving Average."""
    return df["close"].ewm(
        span=period,
        adjust=False,
        min_periods=period
    ).mean()


def calculate_rsi(df, period=14):
    """Calculate RSI using Wilder-style smoothing."""

    delta = df["close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    relative_strength = average_gain / average_loss

    rsi = 100 - (
        100 / (1 + relative_strength)
    )

    return rsi


def calculate_atr(df, period=14):
    """Calculate Average True Range."""

    previous_close = df["close"].shift(1)

    high_low = df["high"] - df["low"]

    high_previous_close = (
        df["high"] - previous_close
    ).abs()

    low_previous_close = (
        df["low"] - previous_close
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_previous_close,
            low_previous_close,
        ],
        axis=1
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period
    ).mean()

    return atr


def calculate_returns(df):
    """Calculate percentage price returns."""

    return df["close"].pct_change()


def add_technical_features(
    df,
    sma_period=20,
    ema_period=20,
    rsi_period=14,
    atr_period=14,
):
    """Add technical indicators to the dataframe."""

    result = df.copy()

    result["sma"] = calculate_sma(
        result,
        sma_period
    )

    result["ema"] = calculate_ema(
        result,
        ema_period
    )

    result["rsi"] = calculate_rsi(
        result,
        rsi_period
    )

    result["atr"] = calculate_atr(
        result,
        atr_period
    )

    result["returns"] = calculate_returns(
        result
    )

    return result