import pandas as pd
import pytest

from engines.breakout_detection import add_breakout_signals


def make_data(closes, resistance=100.0, support=90.0):
    return pd.DataFrame({
        "close": closes,
        "swing_high_price": [resistance] * len(closes),
        "swing_low_price": [support] * len(closes),
    })


def test_close_crossing_above_resistance_triggers_bullish_signal():
    result = add_breakout_signals(make_data([99.0, 101.0]))
    assert result["breakout_signal"].tolist() == [0, 1]


def test_close_crossing_below_support_triggers_bearish_signal():
    result = add_breakout_signals(make_data([91.0, 89.0]))
    assert result["breakout_signal"].tolist() == [0, -1]


def test_close_that_does_not_cross_level_does_not_trigger():
    result = add_breakout_signals(make_data([99.0, 99.5]))
    assert result["breakout_signal"].tolist() == [0, 0]


def test_remaining_beyond_level_does_not_repeat_signal():
    result = add_breakout_signals(make_data([99.0, 101.0, 102.0]))
    assert result["breakout_signal"].tolist() == [0, 1, 0]


def test_newly_available_level_is_not_used_on_same_row():
    df = pd.DataFrame({
        "close": [99.0, 105.0],
        "swing_high_price": [None, 100.0],
        "swing_low_price": [None, 90.0],
    })
    result = add_breakout_signals(df)
    assert result["breakout_signal"].tolist() == [0, 0]


def test_missing_levels_do_not_trigger_signals():
    df = pd.DataFrame({
        "close": [99.0, 101.0, 89.0],
        "swing_high_price": [None, None, None],
        "swing_low_price": [None, None, None],
    })
    result = add_breakout_signals(df)
    assert result["breakout_signal"].tolist() == [0, 0, 0]


def test_input_dataframe_is_not_modified():
    df = make_data([99.0, 101.0])
    original = df.copy(deep=True)
    add_breakout_signals(df)
    pd.testing.assert_frame_equal(df, original)


def test_missing_required_column_raises_value_error():
    df = pd.DataFrame({"close": [99.0, 101.0]})
    with pytest.raises(ValueError, match="Missing required columns"):
        add_breakout_signals(df)

def test_breakout_uses_level_known_before_current_candle():
    df = pd.DataFrame({
        "close": [99.0, 101.0, 102.0],
        "swing_high_price": [100.0, 105.0, 103.0],
        "swing_low_price": [90.0, 90.0, 90.0],
    })

    result = add_breakout_signals(df)

    # On row 1, the available resistance is row 0's level (100).
    # On row 2, the available resistance is row 1's level (105).
    # The current candle's newly displayed level must not be used.
    assert result["breakout_signal"].tolist() == [0, 1, 0]
