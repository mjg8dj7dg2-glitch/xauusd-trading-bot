import pandas as pd


REQUIRED_COLUMNS = ["high", "low"]


def add_market_structure(
    df,
    left_bars=2,
    right_bars=2,
):
    """
    Add confirmed swing-high and swing-low markers.

    A swing is confirmed only after the required number of later
    candles is available. Markers are placed on the confirmation
    candle to avoid exposing a pivot before it could be known.

    Columns added:
        swing_high: high price of a newly confirmed swing high, else NaN
        swing_low: low price of a newly confirmed swing low, else NaN
        swing_high_price: latest confirmed swing-high price, forward-filled
        swing_low_price: latest confirmed swing-low price, forward-filled

    Equal highs or lows within the comparison window disqualify a swing.
    The input DataFrame is not modified.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    if isinstance(left_bars, bool) or not isinstance(left_bars, int):
        raise TypeError("left_bars must be an integer.")
    if isinstance(right_bars, bool) or not isinstance(right_bars, int):
        raise TypeError("right_bars must be an integer.")

    if left_bars < 1 or right_bars < 1:
        raise ValueError("left_bars and right_bars must be at least 1.")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing)
        )

    for column in REQUIRED_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise TypeError(f"Column '{column}' must be numeric.")
        if df[column].isna().any():
            raise ValueError(f"Column '{column}' contains missing values.")

    if (df["high"] < df["low"]).any():
        raise ValueError("Found a candle where high is below low.")

    result = df.copy()
    row_count = len(result)

    swing_high = [float("nan")] * row_count
    swing_low = [float("nan")] * row_count

    high_values = result["high"].tolist()
    low_values = result["low"].tolist()
    window_size = left_bars + right_bars + 1

    for confirm_index in range(left_bars + right_bars, row_count):
        pivot_index = confirm_index - right_bars
        start_index = pivot_index - left_bars
        end_index = pivot_index + right_bars + 1

        high_window = high_values[start_index:end_index]
        low_window = low_values[start_index:end_index]

        pivot_high = high_values[pivot_index]
        pivot_low = low_values[pivot_index]

        if len(high_window) == window_size:
            if pivot_high == max(high_window) and high_window.count(pivot_high) == 1:
                swing_high[confirm_index] = pivot_high

            if pivot_low == min(low_window) and low_window.count(pivot_low) == 1:
                swing_low[confirm_index] = pivot_low

    result["swing_high"] = swing_high
    result["swing_low"] = swing_low
    result["swing_high_price"] = result["swing_high"].ffill()
    result["swing_low_price"] = result["swing_low"].ffill()

    return result
