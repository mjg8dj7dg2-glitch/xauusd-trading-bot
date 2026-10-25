from engines.backtest import BacktestEngine


def test_five_consecutive_losses_reach_pause_threshold():
    engine = BacktestEngine(maximum_consecutive_losses=5)

    for _ in range(5):
        engine._update_losing_streak(-10.0)

    assert engine.current_losing_streak == 5
    assert engine.losing_streak_paused is True


def test_winning_trade_resets_losing_streak():
    engine = BacktestEngine(maximum_consecutive_losses=5)

    for _ in range(4):
        engine._update_losing_streak(-10.0)

    engine._update_losing_streak(20.0)

    assert engine.current_losing_streak == 0
    assert engine.losing_streak_paused is False


def test_breakeven_does_not_change_losing_streak():
    engine = BacktestEngine(maximum_consecutive_losses=5)

    for _ in range(3):
        engine._update_losing_streak(-10.0)

    engine._update_losing_streak(0.0)

    assert engine.current_losing_streak == 3
    assert engine.losing_streak_paused is False


def test_streak_state_resets_for_a_new_run():
    engine = BacktestEngine(maximum_consecutive_losses=5)

    for _ in range(5):
        engine._update_losing_streak(-10.0)

    assert engine.losing_streak_paused is True

    import pandas as pd
    engine.run(pd.DataFrame([{"signal": "NO_SIGNAL"}]))

    assert engine.current_losing_streak == 0
    assert engine.losing_streak_paused is False

def test_paused_streak_blocks_new_entry_and_logs_reason():
    import pandas as pd

    engine = BacktestEngine(maximum_consecutive_losses=1)
    engine.check_risk = lambda data, row, signal: (True, [], None, None)
    engine.analyze_trade_memory = lambda row, signal: None

    data = pd.DataFrame([
        {
            "timestamp": "2026-01-01 00:00:00",
            "signal": "LONG",
            "close": 2000.0,
            "high": 2001.0,
            "low": 1999.0,
            "atr": 2.0,
        },
        {
            "timestamp": "2026-01-01 00:05:00",
            "signal": "NO_SIGNAL",
            "close": 1995.0,
            "high": 1997.0,
            "low": 1995.0,
            "atr": 2.0,
        },
        {
            "timestamp": "2026-01-01 00:10:00",
            "signal": "LONG",
            "close": 1995.0,
            "high": 1996.0,
            "low": 1994.0,
            "atr": 2.0,
        },
    ])

    result = engine.run(data)

    assert result["total_trades"] == 1
    assert result["trades"][0]["pnl"] < 0

    blocked = [
        event for event in result["risk_events"]
        if event["action"] == "BLOCKED_LOSING_STREAK"
    ]
    assert len(blocked) == 1
    assert blocked[0]["allowed"] is False
    assert "BLOCKED_LOSING_STREAK" in blocked[0]["reasons"][0]


def test_backtest_blocks_during_cooldown_then_resumes():
    import pandas as pd

    engine = BacktestEngine(
        maximum_consecutive_losses=1,
        losing_streak_cooldown_candles=12,
    )
    engine.check_risk = lambda data, row, signal: (True, [], None, None)
    engine.analyze_trade_memory = lambda row, signal: None

    rows = []
    for index in range(16):
        if index == 0:
            signal = "LONG"
            close, high, low = 2000.0, 2001.0, 1999.0
        elif index == 1:
            # Hit the first trade's stop-loss; cooldown starts here.
            signal = "NO_SIGNAL"
            close, high, low = 1995.0, 1997.0, 1995.0
        elif 2 <= index <= 14:
            signal = "LONG"
            close, high, low = 1995.0, 1996.0, 1994.0
        else:
            signal = "NO_SIGNAL"
            close, high, low = 1995.0, 1996.0, 1994.0

        rows.append({
            "timestamp": pd.Timestamp("2026-01-01") +
                         pd.Timedelta(minutes=5 * index),
            "signal": signal,
            "close": close,
            "high": high,
            "low": low,
            "atr": 2.0,
        })

    result = engine.run(pd.DataFrame(rows))

    # First trade loses at candle 1; the next entry is at candle 14.
    assert result["total_trades"] == 2
    assert result["trades"][0]["pnl"] < 0
    assert result["trades"][1]["entry_time"] == rows[14]["timestamp"]

    blocked = [
        event for event in result["risk_events"]
        if event.get("action") == "BLOCKED_LOSING_STREAK"
    ]

    # Candles 2?13 are blocked: exactly 12 candles.
    assert len(blocked) == 12
    assert [
        event["timestamp"] for event in blocked
    ] == [rows[index]["timestamp"] for index in range(2, 14)]

    # The cooldown expiry resets the old streak.
    assert engine.current_losing_streak == 0
    assert engine.losing_streak_paused is False
    engine = BacktestEngine(
        maximum_consecutive_losses=5,
        losing_streak_cooldown_candles=12,
    )

    # Simulate the fifth loss closing at candle index 100.
    engine._update_losing_streak(-10.0)
    engine._update_losing_streak(-10.0)
    engine._update_losing_streak(-10.0)
    engine._update_losing_streak(-10.0)
    engine._current_candle_index = 100
    engine._update_losing_streak(-10.0, candle_index=100)

    assert engine.losing_streak_paused is True
    assert engine.losing_streak_pause_until_index == 113

    # Candles 101 through 112 remain paused.
    for index in range(101, 113):
        if index >= engine.losing_streak_pause_until_index:
            engine.losing_streak_paused = False
        assert engine.losing_streak_paused is True

    # Candle 113 is the first eligible candle.
    if 113 >= engine.losing_streak_pause_until_index:
        engine.losing_streak_paused = False

    assert engine.losing_streak_paused is False
