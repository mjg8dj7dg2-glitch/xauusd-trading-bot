from __future__ import annotations

from pathlib import Path

import pandas as pd

from engines.pipeline import TradingPipeline
from engines.backtest import BacktestEngine


DATA_FILE = Path(
    "data",
    "xauusd",
    "raw",
    "XAUUSD_5m.csv",
)


def block_short_atr_8_12(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    mask = (
        (result["signal"] == "SHORT")
        & (result["atr"] >= 8.0)
        & (result["atr"] < 12.0)
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by V5: SHORT + ATR 8-12"
    )

    return result


def block_low_vol_thursday(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    timestamp = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    mask = (
        result["signal"].isin(["LONG", "SHORT"])
        & (
            result["volatility_regime"]
            == "LOW_VOLATILITY"
        )
        & (timestamp.dt.dayofweek == 3)
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by V5: LOW_VOLATILITY + Thursday"
    )

    return result


def apply_v5(df: pd.DataFrame) -> pd.DataFrame:
    result = block_short_atr_8_12(df)
    result = block_low_vol_thursday(result)
    return result


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_trades(result):
    trades = result.get("trades", [])

    if isinstance(trades, pd.DataFrame):
        return trades.to_dict("records")

    if isinstance(trades, list):
        return [
            dict(trade)
            for trade in trades
            if isinstance(trade, dict)
        ]

    return []


def longest_losing_streak(trades):
    longest = 0
    current = 0
    end_index = None

    for index, trade in enumerate(trades):
        pnl = safe_float(
            trade.get("pnl")
        )

        if pnl < 0:
            current += 1

            if current > longest:
                longest = current
                end_index = index

        else:
            current = 0

    if end_index is None:
        return 0, None

    return longest, end_index


def print_trade(index, trade):
    entry = trade.get(
        "entry_time",
        trade.get("timestamp", "?"),
    )

    exit_time = trade.get(
        "exit_time",
        "?",
    )

    direction = trade.get(
        "direction",
        "?",
    )

    pnl = safe_float(
        trade.get("pnl")
    )

    result = trade.get(
        "result",
        trade.get("exit_reason", "?"),
    )

    regime = trade.get(
        "trend_regime",
        trade.get("regime", "?"),
    )

    volatility = trade.get(
        "volatility_regime",
        "?",
    )

    rsi = trade.get(
        "rsi",
        "?",
    )

    atr = trade.get(
        "atr",
        "?",
    )

    entry_price = trade.get(
        "entry_price",
        "?",
    )

    exit_price = trade.get(
        "exit_price",
        "?",
    )

    print(
        f"{index:3d} | "
        f"{str(entry):25s} | "
        f"{direction:5s} | "
        f"PnL {pnl:9.2f} | "
        f"{str(result):12s} | "
        f"{str(regime):14s} | "
        f"{str(volatility):16s} | "
        f"RSI {str(rsi):8s} | "
        f"ATR {str(atr):8s} | "
        f"{entry_price} -> {exit_price}"
    )


def main():
    print("=" * 100)
    print("V5 LOSING-STREAK DIAGNOSTIC")
    print("=" * 100)

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Market data file not found: {DATA_FILE}"
        )

    print()
    print("[1/5] Loading and analyzing XAUUSD data...")

    pipeline = TradingPipeline()

    pipeline_report = pipeline.run(
        DATA_FILE
    )

    analyzed_data = pipeline_report.get(
        "data"
    )

    if analyzed_data is None:
        analyzed_data = pipeline_report.get(
            "analyzed_data"
        )

    if not isinstance(
        analyzed_data,
        pd.DataFrame,
    ):
        raise TypeError(
            "Pipeline did not return a pandas DataFrame."
        )

    print(
        f"PASS: {len(analyzed_data):,} rows analyzed"
    )

    print()
    print("[2/5] Applying exact V5 rules...")

    v5_data = apply_v5(
        analyzed_data
    )

    original_signals = int(
        analyzed_data["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    remaining_signals = int(
        v5_data["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    blocked = (
        original_signals
        - remaining_signals
    )

    print(
        f"Original LONG/SHORT signals : "
        f"{original_signals}"
    )

    print(
        f"V5 blocked signals          : "
        f"{blocked}"
    )

    print(
        f"V5 remaining signals        : "
        f"{remaining_signals}"
    )

    if original_signals != 471:
        raise AssertionError(
            "Unexpected original signal count."
        )

    if blocked != 189:
        raise AssertionError(
            "Unexpected V5 blocked signal count."
        )

    if remaining_signals != 282:
        raise AssertionError(
            "Unexpected V5 remaining signal count."
        )

    print(
        "PASS: exact V5 signal filtering verified"
    )

    print()
    print("[3/5] Running V5 backtest...")

    backtester = BacktestEngine(
        initial_balance=10_000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
    )

    result = backtester.run(
        v5_data
    )

    trades = get_trades(
        result
    )

    if not trades:
        raise AssertionError(
            "V5 backtest returned no trades."
        )

    print(
        f"PASS: {len(trades)} V5 trades returned"
    )

    print()
    print("[4/5] Finding the longest losing streak...")

    longest, end_index = (
        longest_losing_streak(
            trades
        )
    )

    print()
    print(
        f"Longest losing streak: "
        f"{longest} trades"
    )

    if end_index is None:
        print(
            "No losing streak found."
        )
    else:
        start_index = (
            end_index
            - longest
            + 1
        )

        print(
            f"Streak trade range: "
            f"{start_index + 1}"
            f"-"
            f"{end_index + 1}"
        )

        print()
        print(
            "LOSING-STREAK TRADES"
        )
        print(
            "-" * 100
        )

        print(
            "No. | Entry time                | "
            "Dir   | PnL       | Result       | "
            "Trend          | Volatility       | "
            "RSI      | ATR      | Prices"
        )

        print(
            "-" * 100
        )

        for index in range(
            start_index,
            end_index + 1,
        ):
            print_trade(
                index + 1,
                trades[index],
            )

        print()
        print(
            "STREAK CONTEXT"
        )
        print(
            "-" * 100
        )

        streak_trades = trades[
            start_index:
            end_index + 1
        ]

        streak_pnl = sum(
            safe_float(
                trade.get("pnl")
            )
            for trade in streak_trades
        )

        print(
            f"Streak length : "
            f"{len(streak_trades)}"
        )

        print(
            f"Streak P&L    : "
            f"{streak_pnl:+.2f}"
        )

        directions = {}

        regimes = {}

        volatilities = {}

        exit_results = {}

        for trade in streak_trades:
            direction = str(
                trade.get(
                    "direction",
                    "UNKNOWN",
                )
            )

            regime = str(
                trade.get(
                    "trend_regime",
                    trade.get(
                        "regime",
                        "UNKNOWN",
                    ),
                )
            )

            volatility = str(
                trade.get(
                    "volatility_regime",
                    "UNKNOWN",
                )
            )

            exit_result = str(
                trade.get(
                    "result",
                    trade.get(
                        "exit_reason",
                        "UNKNOWN",
                    ),
                )
            )

            directions[direction] = (
                directions.get(
                    direction,
                    0,
                )
                + 1
            )

            regimes[regime] = (
                regimes.get(
                    regime,
                    0,
                )
                + 1
            )

            volatilities[volatility] = (
                volatilities.get(
                    volatility,
                    0,
                )
                + 1
            )

            exit_results[exit_result] = (
                exit_results.get(
                    exit_result,
                    0,
                )
                + 1
            )

        print(
            f"Directions   : {directions}"
        )

        print(
            f"Trend regimes: {regimes}"
        )

        print(
            f"Volatility   : {volatilities}"
        )

        print(
            f"Exit results : {exit_results}"
        )

    print()
    print("[5/5] Comparing losing trades with winning trades...")

    losing_trades = [
        trade
        for trade in trades
        if safe_float(
            trade.get("pnl")
        ) < 0
    ]

    winning_trades = [
        trade
        for trade in trades
        if safe_float(
            trade.get("pnl")
        ) > 0
    ]

    def distribution(
        items,
        key,
        fallback="UNKNOWN",
    ):
        counts = {}

        for trade in items:
            value = trade.get(
                key,
                fallback,
            )

            value = str(
                value
                if value is not None
                else fallback
            )

            counts[value] = (
                counts.get(
                    value,
                    0,
                )
                + 1
            )

        return counts

    print()
    print(
        f"Losing trades : "
        f"{len(losing_trades)}"
    )

    print(
        f"Winning trades: "
        f"{len(winning_trades)}"
    )

    print()
    print(
        "LOSING-TRADE REGIMES"
    )

    print(
        distribution(
            losing_trades,
            "trend_regime",
        )
    )

    print()
    print(
        "WINNING-TRADE REGIMES"
    )

    print(
        distribution(
            winning_trades,
            "trend_regime",
        )
    )

    print()
    print(
        "LOSING-TRADE VOLATILITY"
    )

    print(
        distribution(
            losing_trades,
            "volatility_regime",
        )
    )

    print()
    print(
        "WINNING-TRADE VOLATILITY"
    )

    print(
        distribution(
            winning_trades,
            "volatility_regime",
        )
    )

    print()
    print(
        "LOSING-TRADE DIRECTIONS"
    )

    print(
        distribution(
            losing_trades,
            "direction",
        )
    )

    print()
    print(
        "WINNING-TRADE DIRECTIONS"
    )

    print(
        distribution(
            winning_trades,
            "direction",
        )
    )

    print()
    print(
        "=" * 100
    )
    print(
        "V5 LOSING-STREAK DIAGNOSTIC COMPLETE"
    )
    print(
        "=" * 100
    )


if __name__ == "__main__":
    main()