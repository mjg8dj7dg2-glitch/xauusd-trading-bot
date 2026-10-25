import pandas as pd


def calculate_volatility(df, period=14):
    """Calculate rolling volatility from percentage returns."""

    returns = df["close"].pct_change()

    volatility = returns.rolling(
        window=period,
        min_periods=period
    ).std()

    return volatility


def classify_volatility(
    volatility,
    low_threshold=0.005,
    high_threshold=0.015
):
    """Classify the current volatility environment."""

    if pd.isna(volatility):
        return "UNKNOWN"

    if volatility < low_threshold:
        return "LOW_VOLATILITY"

    if volatility >= high_threshold:
        return "HIGH_VOLATILITY"

    return "NORMAL_VOLATILITY"


def classify_trend(
    df,
    fast_period=5,
    slow_period=10,
    threshold=0.001
):
    """Classify the market trend using moving averages."""

    fast_ema = df["close"].ewm(
        span=fast_period,
        adjust=False
    ).mean()

    slow_ema = df["close"].ewm(
        span=slow_period,
        adjust=False
    ).mean()

    difference = (
        fast_ema - slow_ema
    ) / slow_ema

    trend = []

    for value in difference:

        if pd.isna(value):
            trend.append("UNKNOWN")

        elif value > threshold:
            trend.append("TRENDING_UP")

        elif value < -threshold:
            trend.append("TRENDING_DOWN")

        else:
            trend.append("RANGING")

    return pd.Series(
        trend,
        index=df.index
    )


def add_market_regime(
    df,
    volatility_period=5,
    fast_period=3,
    slow_period=6,
    trend_threshold=0.001,
):
    """Add trend and volatility regime information."""

    result = df.copy()

    result["volatility"] = calculate_volatility(
        result,
        volatility_period
    )

    result["volatility_regime"] = (
        result["volatility"]
        .apply(classify_volatility)
    )

    result["trend_regime"] = classify_trend(
        result,
        fast_period,
        slow_period,
        trend_threshold
    )

    return result