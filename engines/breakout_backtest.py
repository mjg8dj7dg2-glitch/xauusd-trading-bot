from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from engines.market_structure import add_market_structure
from engines.breakout_detection import add_breakout_signals


@dataclass
class BreakoutConfig:
    initial_balance: float = 10_000.0
    risk_fraction: float = 0.005
    daily_loss_fraction: float = 0.01
    stop_atr_multiplier: float = 1.5
    reward_risk_ratio: float = 2.0
    atr_period: int = 14
    left_bars: int = 2
    right_bars: int = 2
    max_consecutive_losses: int = 3

    # Explicit assumptions, not broker specifications.
    # P&L = price change * quantity * value_per_price_unit.
    value_per_price_unit: float = 1.0
    spread_price: float = 0.30
    slippage_price_per_side: float = 0.05
    commission_per_unit_per_side: float = 0.0


def _prepare_data(df, config):
    required = ["datetime", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    data = df.copy()
    data["datetime"] = pd.to_datetime(data["datetime"], utc=True, errors="raise")
    if data["datetime"].isna().any():
        raise ValueError("datetime contains missing values")
    if data["datetime"].duplicated().any():
        raise ValueError("Duplicate timestamps are not allowed")
    if not data["datetime"].is_monotonic_increasing:
        raise ValueError("Data must be sorted chronologically")

    for col in ["open", "high", "low", "close"]:
        data[col] = pd.to_numeric(data[col], errors="raise")
    prices = data[["open", "high", "low", "close"]]
    if not np.isfinite(prices.to_numpy()).all():
        raise ValueError("OHLC values must be finite")
    if (
        (data["high"] < data["low"]).any()
        or (data["high"] < data[["open", "close"]].max(axis=1)).any()
        or (data["low"] > data[["open", "close"]].min(axis=1)).any()
    ):
        raise ValueError("Invalid OHLC candle")

    if len(data) < 2:
        raise ValueError("At least two candles are required")
    if config.initial_balance <= 0:
        raise ValueError("initial_balance must be positive")
    if not 0 < config.risk_fraction < 1:
        raise ValueError("risk_fraction must be between 0 and 1")
    if not 0 < config.daily_loss_fraction < 1:
        raise ValueError("daily_loss_fraction must be between 0 and 1")
    if config.stop_atr_multiplier <= 0 or config.reward_risk_ratio <= 0:
        raise ValueError("Stop multiplier and reward/risk ratio must be positive")
    if config.atr_period < 1 or config.left_bars < 1 or config.right_bars < 1:
        raise ValueError("ATR period and swing bar counts must be positive")
    if config.max_consecutive_losses < 1:
        raise ValueError("max_consecutive_losses must be positive")
    if (
        config.value_per_price_unit <= 0
        or config.spread_price < 0
        or config.slippage_price_per_side < 0
        or config.commission_per_unit_per_side < 0
    ):
        raise ValueError("Invalid execution-cost or contract-value assumption")

    # Gaps are preserved; no synthetic candles are inserted.
    return data.reset_index(drop=True)


def _add_atr(data, period):
    previous_close = data["close"].shift(1)
    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    data["atr"] = true_range.ewm(
        alpha=1 / period, adjust=False, min_periods=period
    ).mean()
    return data


def backtest_breakouts(df, config=None):
    """Run a standalone, close-confirmed breakout simulation.

    Signals are generated on completed candles and entered at the next
    candle's open. Daily loss and loss-streak halts block new entries;
    existing positions continue to use their stop/target rules.
    """
    cfg = config or BreakoutConfig()
    data = _prepare_data(df, cfg)
    data = _add_atr(data, cfg.atr_period)
    data = add_market_structure(
        data, left_bars=cfg.left_bars, right_bars=cfg.right_bars
    )
    data = add_breakout_signals(data)

    balance = cfg.initial_balance
    position = None
    trades = []
    equity_rows = []
    day = None
    day_start_equity = balance
    losing_streak = 0
    halted_today = False
    loss_streak_halt_day = None

    half_spread = cfg.spread_price / 2
    side_cost = half_spread + cfg.slippage_price_per_side
    value = cfg.value_per_price_unit

    def unrealized(mark):
        if position is None:
            return 0.0
        direction = position["direction"]
        qty = position["quantity"]
        gross = (mark - position["entry_price"]) * direction * qty * value
        exit_cost = (side_cost * qty * value
                     + qty * cfg.commission_per_unit_per_side)
        return gross - position["entry_commission"] - exit_cost

    def close_position(raw_price, timestamp, reason):
        nonlocal balance, position, losing_streak, loss_streak_halt_day
        p = position
        exit_price = raw_price - p["direction"] * side_cost
        exit_commission = p["quantity"] * cfg.commission_per_unit_per_side
        gross = (
            (exit_price - p["entry_price"])
            * p["direction"] * p["quantity"] * value
        )
        pnl = gross - p["entry_commission"] - exit_commission
        balance += pnl
        trade = {
            "entry_time": p["entry_time"],
            "exit_time": timestamp,
            "direction": "long" if p["direction"] == 1 else "short",
            "entry_price": p["entry_price"],
            "exit_price": exit_price,
            "stop_price": p["stop_price"],
            "target_price": p["target_price"],
            "quantity": p["quantity"],
            "pnl": pnl,
            "r_multiple": pnl / p["risk_cash"] if p["risk_cash"] else 0.0,
            "exit_reason": reason,
            "balance_after": balance,
        }
        trades.append(trade)
        losing_streak = losing_streak + 1 if pnl < 0 else 0

        if losing_streak >= cfg.max_consecutive_losses:
            loss_streak_halt_day = timestamp.date()

        position = None

    for i in range(len(data)):
        row = data.iloc[i]
        timestamp = row["datetime"]
        current_day = timestamp.date()

        if current_day != day:
            # Start the UTC day from balance plus any position's marked
            # equity at the previous completed candle.
            if day is not None:
                day_start_equity = balance + unrealized(
                    float(data.iloc[i - 1]["close"])
                )
            else:
                day_start_equity = balance
            day = current_day
            # Consecutive losses persist across UTC day boundaries.
            # Only the daily loss halt resets here.
            halted_today = False

        # A trade already open at the start of this candle can exit at
        # the open if price has gapped beyond its stop or target.
        was_open = position is not None
        if position is not None:
            p = position
            o, h, l = float(row["open"]), float(row["high"]), float(row["low"])
            if p["direction"] == 1 and o <= p["stop_price"]:
                close_position(o, timestamp, "stop_gap")
            elif p["direction"] == 1 and o >= p["target_price"]:
                close_position(o, timestamp, "target_gap")
            elif p["direction"] == -1 and o >= p["stop_price"]:
                close_position(o, timestamp, "stop_gap")
            elif p["direction"] == -1 and o <= p["target_price"]:
                close_position(o, timestamp, "target_gap")
            elif p["direction"] == 1 and l <= p["stop_price"]:
                close_position(p["stop_price"], timestamp, "stop")
            elif p["direction"] == 1 and h >= p["target_price"]:
                close_position(p["target_price"], timestamp, "target")
            elif p["direction"] == -1 and h >= p["stop_price"]:
                close_position(p["stop_price"], timestamp, "stop")
            elif p["direction"] == -1 and l <= p["target_price"]:
                close_position(p["target_price"], timestamp, "target")

        # Check the daily equity limit, including unrealized P&L.
        equity_now = balance + unrealized(float(row["close"]))
        if equity_now <= day_start_equity * (1 - cfg.daily_loss_fraction):
            halted_today = True

        # Signal on the previous completed candle; enter at this candle's
        # open only if no position was open at its start.
        if (
            position is None
            and not was_open
            and i > 0
            and not halted_today
            and loss_streak_halt_day != current_day
        ):
            signal = int(data.iloc[i - 1]["breakout_signal"])
            atr = data.iloc[i - 1]["atr"]
            if signal in (-1, 1) and pd.notna(atr) and atr > 0:
                direction = signal
                raw_open = float(row["open"])
                entry_price = raw_open + direction * side_cost
                stop_distance = float(atr) * cfg.stop_atr_multiplier
                stop_price = entry_price - direction * stop_distance
                target_price = (
                    entry_price
                    + direction * stop_distance * cfg.reward_risk_ratio
                )

                equity_before = balance + unrealized(raw_open)
                risk_cash = max(0.0, equity_before * cfg.risk_fraction)
                risk_per_unit = (
                    (stop_distance + side_cost) * value
                    + 2 * cfg.commission_per_unit_per_side
                )
                quantity = risk_cash / risk_per_unit if risk_per_unit > 0 else 0
                if quantity > 0 and math.isfinite(quantity):
                    entry_commission = (
                        quantity * cfg.commission_per_unit_per_side
                    )
                    position = {
                        "direction": direction,
                        "entry_time": timestamp,
                        "entry_price": entry_price,
                        "stop_price": stop_price,
                        "target_price": target_price,
                        "quantity": quantity,
                        "risk_cash": risk_cash,
                        "entry_commission": entry_commission,
                    }

                    # The stop/target can be reached later in the entry
                    # candle. Stop is checked first if both are touched.
                    h, l = float(row["high"]), float(row["low"])
                    if direction == 1 and l <= stop_price:
                        close_position(stop_price, timestamp, "stop")
                    elif direction == 1 and h >= target_price:
                        close_position(target_price, timestamp, "target")
                    elif direction == -1 and h >= stop_price:
                        close_position(stop_price, timestamp, "stop")
                    elif direction == -1 and l <= target_price:
                        close_position(target_price, timestamp, "target")

                # Recheck after entry and same-candle stop/target processing.
        # This catches a daily equity breach caused by a newly opened
        # position, even if equity recovers on the next candle.
        equity_at_close = balance + unrealized(float(row["close"]))
        if equity_at_close <= day_start_equity * (
            1 - cfg.daily_loss_fraction
        ):
            halted_today = True

        equity_rows.append({
            "datetime": timestamp,
            "balance": balance,
            "equity": equity_at_close,
        })

    # Close any remaining position at the final observed close.
    if position is not None:
        last = data.iloc[-1]
        close_position(float(last["close"]), last["datetime"], "end_of_data")
        equity_rows[-1]["balance"] = balance
        equity_rows[-1]["equity"] = balance

    trade_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_rows)

    pnls = trade_df["pnl"] if not trade_df.empty else pd.Series(dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(-losses.sum())
    peak = equity_df["equity"].cummax()
    drawdown = (equity_df["equity"] - peak) / peak

    metrics = {
        "initial_balance": cfg.initial_balance,
        "final_balance": balance,
        "net_profit": balance - cfg.initial_balance,
        "trades": int(len(trade_df)),
        "win_rate_pct": float((pnls > 0).mean() * 100) if len(pnls) else 0.0,
        "expectancy_per_trade": float(pnls.mean()) if len(pnls) else 0.0,
        "profit_factor": (
            gross_profit / gross_loss if gross_loss > 0
            else (float("inf") if gross_profit > 0 else 0.0)
        ),
        "max_drawdown_pct": float(-drawdown.min() * 100),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }
    return {
        "metrics": metrics,
        "trades": trade_df,
        "equity_curve": equity_df,
        "signals": data,
    }
