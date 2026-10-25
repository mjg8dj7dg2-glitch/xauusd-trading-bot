
import numpy as np
import pandas as pd
import pytest

from engines.breakout_backtest import BreakoutConfig, backtest_breakouts


def make_candles(n=30):
    return pd.DataFrame({
        "datetime": pd.date_range(
            "2026-08-01 00:00:00", periods=n, freq="5min", tz="UTC"
        ),
        "open": [100.0] * n,
        "high": [101.0] * n,
        "low": [99.0] * n,
        "close": [100.0] * n,
        "volume": [1.0] * n,
    })


def test_no_breakouts_returns_complete_results():
    data = make_candles()
    config = BreakoutConfig(
        initial_balance=10_000.0,
        atr_period=3,
        left_bars=2,
        right_bars=2,
        spread_price=0.0,
        slippage_price_per_side=0.0,
    )

    result = backtest_breakouts(data, config)

    assert set(result) == {"metrics", "trades", "equity_curve", "signals"}
    assert result["trades"].empty
    assert len(result["equity_curve"]) == len(data)
    assert result["metrics"]["initial_balance"] == 10_000.0
    assert result["metrics"]["final_balance"] == pytest.approx(10_000.0)
    assert result["metrics"]["trades"] == 0
    assert np.isfinite(result["equity_curve"]["equity"]).all()
    assert np.isfinite(result["equity_curve"]["balance"]).all()


def test_missing_required_column_is_rejected():
    data = make_candles().drop(columns=["close"])

    with pytest.raises(ValueError, match="Missing required columns"):
        backtest_breakouts(data)


def test_unsorted_timestamps_are_rejected():
    data = make_candles()
    data.loc[[0, 1], "datetime"] = data.loc[[1, 0], "datetime"].to_numpy()

    with pytest.raises(ValueError, match="sorted chronologically"):
        backtest_breakouts(data)


def test_duplicate_timestamps_are_rejected():
    data = make_candles()
    data.loc[1, "datetime"] = data.loc[0, "datetime"]

    with pytest.raises(ValueError, match="Duplicate timestamps"):
        backtest_breakouts(data)


def test_invalid_ohlc_is_rejected():
    data = make_candles()
    data.loc[5, "high"] = 98.0

    with pytest.raises(ValueError, match="Invalid OHLC candle"):
        backtest_breakouts(data)


def test_too_few_candles_are_rejected():
    with pytest.raises(ValueError, match="At least two candles"):
        backtest_breakouts(make_candles(1))


def test_invalid_risk_fraction_is_rejected():
    with pytest.raises(ValueError, match="risk_fraction"):
        backtest_breakouts(
            make_candles(),
            BreakoutConfig(risk_fraction=1.0),
        )


def test_breakout_signal_uses_previously_known_level():
    from engines.breakout_detection import add_breakout_signals

    data = pd.DataFrame({
        "close": [100.0, 100.0, 100.0, 101.0, 102.0],
        "swing_high_price": [np.nan, 100.5, 100.5, 100.5, 100.5],
        "swing_low_price": [np.nan, 99.0, 99.0, 99.0, 99.0],
    })

    result = add_breakout_signals(data)

    assert result.loc[3, "breakout_signal"] == 1
    assert result.loc[0, "breakout_signal"] == 0
    assert result.loc[4, "breakout_signal"] == 0


def test_market_structure_does_not_confirm_swing_before_right_bars():
    from engines.market_structure import add_market_structure

    data = pd.DataFrame({
        "high": [10.0, 11.0, 15.0, 12.0, 11.0, 10.0],
        "low": [8.0, 9.0, 10.0, 9.0, 8.0, 7.0],
    })

    result = add_market_structure(data, left_bars=2, right_bars=2)

    assert pd.isna(result.loc[3, "swing_high"])
    assert result.loc[4, "swing_high"] == 15.0


def test_backtest_trade_records_have_expected_fields():
    data = make_candles(30)
    config = BreakoutConfig(
        atr_period=3,
        left_bars=2,
        right_bars=2,
        spread_price=0.0,
        slippage_price_per_side=0.0,
    )

    result = backtest_breakouts(data, config)

    assert result["trades"].empty
    assert "breakout_signal" in result["signals"].columns
    assert len(result["equity_curve"]) == len(data)


def test_backtest_uses_stop_first_when_stop_and_target_both_hit():
    data = pd.DataFrame({
        "datetime": pd.date_range(
            "2026-08-01 00:00:00", periods=40, freq="5min", tz="UTC"
        ),
        "open": [100.0] * 40,
        "high": [101.0] * 40,
        "low": [99.0] * 40,
        "close": [100.0] * 40,
        "volume": [1.0] * 40,
    })

    data.loc[10, "high"] = 105.0
    data.loc[11, "high"] = 103.0
    data.loc[12, "high"] = 102.0
    data.loc[13, "high"] = 102.0

    data.loc[14, "close"] = 100.0
    data.loc[15, ["open", "high", "low", "close"]] = [
        100.0, 106.0, 99.0, 106.0
    ]
    data.loc[16, ["open", "high", "low", "close"]] = [
        106.0, 110.0, 90.0, 100.0
    ]

    config = BreakoutConfig(
        atr_period=3,
        left_bars=2,
        right_bars=2,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    result = backtest_breakouts(data, config)

    assert not result["trades"].empty
    first_trade = result["trades"].iloc[0]
    assert first_trade["direction"] == "long"
    assert first_trade["exit_reason"] == "stop"
    assert first_trade["exit_price"] == first_trade["stop_price"]


def test_three_losses_halt_entries_until_next_utc_day(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(7)

    data.loc[5, "datetime"] = pd.Timestamp(
        "2026-08-02 00:00:00", tz="UTC"
    )
    data.loc[6, "datetime"] = pd.Timestamp(
        "2026-08-02 00:05:00", tz="UTC"
    )

    signals = [1, 1, 1, 1, 1, 0, 0]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = signals
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        risk_fraction=0.005,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=0.1,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        max_consecutive_losses=3,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    result = backtest_breakouts(data, config)
    trades = result["trades"]

    expected_entry_times = [
        data.loc[i, "datetime"] for i in [1, 2, 3, 5]
    ]

    assert len(trades) == 4
    assert pd.to_datetime(trades["entry_time"]).tolist() == expected_entry_times
    assert (trades["pnl"] < 0).all()
    assert trades["exit_reason"].tolist() == ["stop"] * 4
    assert trades.iloc[2]["exit_time"] == data.loc[3, "datetime"]
    assert data.loc[4, "datetime"] not in set(trades["entry_time"])
    assert trades.iloc[3]["entry_time"] == data.loc[5, "datetime"]
    assert trades.iloc[:3]["exit_time"].dt.date.nunique() == 1
    assert trades.iloc[2]["exit_time"].date() == pd.Timestamp(
        "2026-08-01"
    ).date()
    assert trades.iloc[3]["entry_time"].date() == pd.Timestamp(
        "2026-08-02"
    ).date()


def test_daily_loss_limit_blocks_new_entries(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(8)
    signals = [1] * len(data)

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = signals
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        risk_fraction=0.05,
        daily_loss_fraction=0.01,
        stop_atr_multiplier=0.1,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        max_consecutive_losses=10,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    result = backtest_breakouts(data, config)
    trades = result["trades"]

    assert len(trades) == 1
    assert trades.iloc[0]["pnl"] <= -100.0
    assert trades.iloc[0]["entry_time"] == data.loc[1, "datetime"]


def test_unrealized_daily_loss_blocks_new_entries(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)

    # The long position stays open while closing equity falls below
    # the daily threshold. A later candle reaches the profit target.
    data.loc[1, "close"] = 98.0
    data.loc[1, "low"] = 98.0
    data.loc[1, "close"] = 98.0
    data.loc[2, "close"] = 98.0
    data.loc[2, "low"] = 98.0
    data.loc[3, "high"] = 110.0
    data.loc[3, "close"] = 105.0

    signals = [1] * len(data)

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = signals
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        risk_fraction=0.05,
        daily_loss_fraction=0.01,
        stop_atr_multiplier=1.5,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        max_consecutive_losses=10,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    result = backtest_breakouts(data, config)
    trades = result["trades"]

    # The unrealized loss triggers the daily halt.
    # The existing position subsequently reaches its target.
    assert len(trades) == 1
    assert trades.iloc[0]["entry_time"] == data.loc[1, "datetime"]
    assert trades.iloc[0]["exit_reason"] == "target"
    assert trades.iloc[0]["pnl"] > 0

    # No further entries are allowed after the daily halt.
    assert data.loc[4, "datetime"] not in set(trades["entry_time"])
    assert data.loc[5, "datetime"] not in set(trades["entry_time"])
def test_entry_candle_daily_loss_breach_halts_rest_of_day(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)

    # The first trade's entry-candle closing equity breaches
    # the daily loss threshold without hitting its stop.
    data.loc[1, "close"] = 98.0
    data.loc[1, "low"] = 98.0

    # The position then recovers and reaches its profit target.
    data.loc[2, "high"] = 110.0

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [1] * len(frame)
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        risk_fraction=0.05,
        daily_loss_fraction=0.01,
        stop_atr_multiplier=1.5,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        max_consecutive_losses=10,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    result = backtest_breakouts(data, config)
    trades = result["trades"]

    # The daily halt should remain active even after equity recovers.
    assert len(trades) == 1
    assert trades.iloc[0]["entry_time"] == data.loc[1, "datetime"]
    assert trades.iloc[0]["exit_reason"] == "target"

def test_stop_gap_exits_at_candle_open(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)
    data.loc[2, ["open", "high", "low", "close"]] = [
        97.0, 98.0, 96.0, 97.0
    ]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [1, 0, 0, 0, 0, 0]
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=1.0,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    trades = backtest_breakouts(data, config)["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "long"
    assert trade["stop_price"] == 98.0
    assert trade["exit_reason"] == "stop_gap"
    assert trade["exit_price"] == 97.0


def test_target_gap_exits_at_candle_open(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)
    data.loc[2, ["open", "high", "low", "close"]] = [
        105.0, 106.0, 104.5, 105.5
    ]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [1, 0, 0, 0, 0, 0]
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=1.0,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    trades = backtest_breakouts(data, config)["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "long"
    assert trade["target_price"] == 104.0
    assert trade["exit_reason"] == "target_gap"
    assert trade["exit_price"] == 105.0

def test_short_stop_gap_exits_at_candle_open(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)
    data.loc[2, ["open", "high", "low", "close"]] = [
        103.0, 104.0, 102.5, 103.5
    ]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [-1, 0, 0, 0, 0, 0]
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=1.0,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    trades = backtest_breakouts(data, config)["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "short"
    assert trade["stop_price"] == 102.0
    assert trade["exit_reason"] == "stop_gap"
    assert trade["exit_price"] == 103.0


def test_short_target_gap_exits_at_candle_open(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)
    data.loc[2, ["open", "high", "low", "close"]] = [
        95.0, 95.5, 94.0, 95.0
    ]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [-1, 0, 0, 0, 0, 0]
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=1.0,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    trades = backtest_breakouts(data, config)["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "short"
    assert trade["target_price"] == 96.0
    assert trade["exit_reason"] == "target_gap"
    assert trade["exit_price"] == 95.0
def test_short_entry_candle_uses_stop_when_both_levels_hit(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)
    data.loc[1, ["open", "high", "low", "close"]] = [
        100.0, 103.0, 95.0, 100.0
    ]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [-1, 0, 0, 0, 0, 0]
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=1.0,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    trades = backtest_breakouts(data, config)["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "short"
    assert trade["stop_price"] == 102.0
    assert trade["target_price"] == 96.0
    assert trade["exit_reason"] == "stop"
    assert trade["exit_price"] == trade["stop_price"]
def test_short_entry_candle_target_only_exits_at_target(monkeypatch):
    import engines.breakout_backtest as engine

    data = make_candles(6)
    data.loc[1, ["open", "high", "low", "close"]] = [
        100.0, 101.0, 95.0, 98.0
    ]

    def fake_breakout_signals(frame):
        frame = frame.copy()
        frame["breakout_signal"] = [-1, 0, 0, 0, 0, 0]
        return frame

    monkeypatch.setattr(
        engine, "add_breakout_signals", fake_breakout_signals
    )

    config = BreakoutConfig(
        initial_balance=10_000.0,
        daily_loss_fraction=0.50,
        stop_atr_multiplier=1.0,
        reward_risk_ratio=2.0,
        atr_period=1,
        left_bars=1,
        right_bars=1,
        spread_price=0.0,
        slippage_price_per_side=0.0,
        commission_per_unit_per_side=0.0,
    )

    trades = backtest_breakouts(data, config)["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "short"
    assert trade["target_price"] == 96.0
    assert trade["exit_reason"] == "target"
    assert trade["exit_price"] == trade["target_price"]