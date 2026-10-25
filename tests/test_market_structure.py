import pandas as pd
import pytest

from engines.market_structure import add_market_structure


def make_candles(highs, lows):
    return pd.DataFrame({
        "high": highs,
        "low": lows,
    })


def test_detects_swing_high_only_after_two_later_candles():
    df = make_candles(
        highs=[10, 12, 15, 13, 11],
        lows=[5, 6, 7, 6, 5],
    )

    result = add_market_structure(df, left_bars=2, right_bars=2)

    # The peak at index 2 is not exposed on its original candle.
    assert pd.isna(result.loc[2, "swing_high"])

    # It becomes available on confirmation candle index 4.
    assert result.loc[4, "swing_high"] == 15
    assert result.loc[4, "swing_high_price"] == 15


def test_detects_swing_low_only_after_two_later_candles():
    df = make_candles(
        highs=[15, 14, 12, 14, 15],
        lows=[10, 8, 5, 7, 9],
    )

    result = add_market_structure(df, left_bars=2, right_bars=2)

    assert pd.isna(result.loc[2, "swing_low"])
    assert result.loc[4, "swing_low"] == 5
    assert result.loc[4, "swing_low_price"] == 5


def test_equal_highs_do_not_create_a_swing_high():
    df = make_candles(
        highs=[10, 12, 15, 15, 11],
        lows=[5, 6, 7, 6, 5],
    )

    result = add_market_structure(df, left_bars=2, right_bars=2)

    assert result["swing_high"].isna().all()


def test_equal_lows_do_not_create_a_swing_low():
    df = make_candles(
        highs=[15, 14, 12, 14, 15],
        lows=[10, 8, 5, 5, 9],
    )

    result = add_market_structure(df, left_bars=2, right_bars=2)

    assert result["swing_low"].isna().all()


def test_input_dataframe_is_not_modified():
    df = make_candles(
        highs=[10, 12, 15, 13, 11],
        lows=[5, 6, 7, 6, 5],
    )
    original = df.copy(deep=True)

    add_market_structure(df)

    pd.testing.assert_frame_equal(df, original)


def test_missing_columns_raise_value_error():
    df = pd.DataFrame({"high": [10, 12, 11]})

    with pytest.raises(ValueError, match="Missing required columns"):
        add_market_structure(df)


def test_invalid_bar_counts_are_rejected():
    df = make_candles([10, 12, 11], [5, 6, 4])

    with pytest.raises(ValueError):
        add_market_structure(df, left_bars=0)

    with pytest.raises(TypeError):
        add_market_structure(df, right_bars=1.5)


def test_high_below_low_is_rejected():
    df = make_candles(
        highs=[10, 12, 11],
        lows=[5, 13, 4],
    )

    with pytest.raises(ValueError, match="high is below low"):
        add_market_structure(df)


def test_appending_future_candles_does_not_change_past_outputs():
    initial = make_candles(
        highs=[10, 12, 15, 13, 11],
        lows=[5, 6, 7, 6, 5],
    )
    extended = make_candles(
        highs=[10, 12, 15, 13, 11, 14, 10],
        lows=[5, 6, 7, 6, 5, 8, 4],
    )

    initial_result = add_market_structure(initial)
    extended_result = add_market_structure(extended)

    columns = [
        "swing_high",
        "swing_low",
        "swing_high_price",
        "swing_low_price",
    ]

    pd.testing.assert_frame_equal(
        initial_result[columns],
        extended_result.loc[:len(initial) - 1, columns],
    )
