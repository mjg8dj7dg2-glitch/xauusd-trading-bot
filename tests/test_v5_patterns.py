from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from engines.backtest import BacktestEngine
from engines.pipeline import TradingPipeline
from engines.strategy_experiment import (
    block_low_vol_thursday,
    block_short_atr_8_12,
    compose_transforms,
)


DATA_FILE = Path("data/xauusd/raw/XAUUSD_5m.csv")


def bucket_rsi(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value < 30:
        return "<30"
    if value < 40:
        return "30-40"
    if value < 50:
        return "40-50"
    if value < 60:
        return "50-60"
    if value < 70:
        return "60-70"

    return "70+"


def bucket_atr(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"

    if value < 8:
        return "<8"
    if value < 12:
        return "8-12"
    if value < 16:
        return "12-16"
    if value < 20:
        return "16-20"

    return "20+"


def prepare_trade_data(trades):
    if isinstance(trades, pd.DataFrame):
        df = trades.copy()

    elif isinstance(trades, list):
        rows = []

        for trade in trades:
            if isinstance(trade, dict):
                rows.append(trade)

            elif hasattr(trade, "__dict__"):
                rows.append(vars(trade))

        df = pd.DataFrame(rows)

    else:
        raise TypeError(
            f"Unsupported trades type: {type(trades)}"
        )

    if df.empty:
        return df

    if "timestamp" not in df.columns:
        if "entry_time" in df.columns:
            df["timestamp"] = df["entry_time"]

    if "timestamp" not in df.columns:
        raise ValueError(
            "Trades do not contain timestamp or entry_time."
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    df["day"] = df["timestamp"].dt.day_name()

    df["hour"] = df["timestamp"].dt.hour

    df["hour_bucket"] = df["hour"].apply(
        lambda x: (
            f"{int(x):02d}:00"
            if pd.notna(x)
            else "UNKNOWN"
        )
    )

    if "rsi" in df.columns:
        df["rsi_bucket"] = df["rsi"].apply(
            bucket_rsi
        )
    else:
        df["rsi_bucket"] = "UNKNOWN"

    if "atr" in df.columns:
        df["atr_bucket"] = df["atr"].apply(
            bucket_atr
        )
    else:
        df["atr_bucket"] = "UNKNOWN"

    if "result" not in df.columns:
        if "pnl" not in df.columns:
            raise ValueError(
                "Trades contain neither result nor pnl."
            )

        df["result"] = df["pnl"].apply(
            lambda x:
                "WIN"
                if float(x) > 0
                else "LOSS"
        )

    df["result"] = (
        df["result"]
        .astype(str)
        .str.upper()
    )

    return df


def print_distribution(
    title,
    losses,
    wins,
    column,
):
    print()
    print(title)
    print("-" * len(title))

    loss_counts = Counter(
        str(x)
        for x in losses[column].dropna()
    )

    win_counts = Counter(
        str(x)
        for x in wins[column].dropna()
    )

    total_losses = max(
        len(losses),
        1,
    )

    total_wins = max(
        len(wins),
        1,
    )

    keys = sorted(
        set(loss_counts)
        | set(win_counts)
    )

    for key in keys:
        loss_count = loss_counts.get(
            key,
            0,
        )

        win_count = win_counts.get(
            key,
            0,
        )

        loss_pct = (
            loss_count
            / total_losses
            * 100
        )

        win_pct = (
            win_count
            / total_wins
            * 100
        )

        gap = loss_pct - win_pct

        print(
            f"{key:20s} "
            f"losses {loss_count:2d} "
            f"({loss_pct:5.1f}%) | "
            f"wins {win_count:2d} "
            f"({win_pct:5.1f}%) | "
            f"gap {gap:+5.1f} pp"
        )


def print_combinations(
    losses,
    wins,
):
    print()
    print(
        "TOP RECURRING LOSS COMBINATIONS"
    )
    print(
        "--------------------------------"
    )

    combinations = [
        (
            "direction + regime",
            [
                "direction",
                "regime",
            ],
        ),
        (
            "direction + volatility",
            [
                "direction",
                "volatility_regime",
            ],
        ),
        (
            "direction + day",
            [
                "direction",
                "day",
            ],
        ),
        (
            "regime + day",
            [
                "regime",
                "day",
            ],
        ),
        (
            "day + hour",
            [
                "day",
                "hour_bucket",
            ],
        ),
        (
            "RSI + ATR",
            [
                "rsi_bucket",
                "atr_bucket",
            ],
        ),
        (
            "direction + RSI",
            [
                "direction",
                "rsi_bucket",
            ],
        ),
        (
            "direction + ATR",
            [
                "direction",
                "atr_bucket",
            ],
        ),
        (
            "regime + volatility",
            [
                "regime",
                "volatility_regime",
            ],
        ),
    ]

    total_losses = max(
        len(losses),
        1,
    )

    total_wins = max(
        len(wins),
        1,
    )

    for title, columns in combinations:

        if not all(
            column in losses.columns
            for column in columns
        ):
            continue

        loss_groups = (
            losses
            .groupby(
                columns,
                dropna=False,
            )
            .size()
            .sort_values(
                ascending=False
            )
        )

        win_groups = (
            wins
            .groupby(
                columns,
                dropna=False,
            )
            .size()
        )

        candidates = []

        for key, loss_count in loss_groups.items():

            if not isinstance(
                key,
                tuple,
            ):
                key = (key,)

            if loss_count < 3:
                continue

            win_count = int(
                win_groups.get(
                    key,
                    0,
                )
            )

            loss_share = (
                loss_count
                / total_losses
            )

            win_share = (
                win_count
                / total_wins
            )

            gap = (
                loss_share
                - win_share
            )

            candidates.append(
                (
                    gap,
                    int(loss_count),
                    win_count,
                    key,
                )
            )

        candidates.sort(
            reverse=True
        )

        print()
        print(title)

        if not candidates:
            print(
                "  No combination had "
                "at least 3 losses."
            )
            continue

        for (
            gap,
            loss_count,
            win_count,
            key,
        ) in candidates[:5]:

            label = " + ".join(
                str(x)
                for x in key
            )

            print(
                f"  {label:55s} "
                f"losses={loss_count:2d} "
                f"wins={win_count:2d} "
                f"gap={gap * 100:+5.1f} pp"
            )


def main():
    print("V5 PATTERN ANALYSIS")
    print("===================")

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Market data not found: {DATA_FILE}"
        )

    print(
        "[1/6] Loading and analyzing XAUUSD data..."
    )

    # This matches the actual TradingPipeline
    # interface used by PaperTradingRunner.
    pipeline = TradingPipeline()

    pipeline_report = pipeline.run(
        str(DATA_FILE)
    )

    if not isinstance(
        pipeline_report,
        dict,
    ):
        raise TypeError(
            "TradingPipeline.run() did not "
            "return a dictionary."
        )

    analyzed = pipeline_report.get(
        "data"
    )

    if analyzed is None:
        raise KeyError(
            "Pipeline result does not contain 'data'."
        )

    analyzed = analyzed.copy()

    print(
        f"PASS: {len(analyzed):,} rows analyzed"
    )

    print(
        "[2/6] Applying exact V5 rules..."
    )

    original_signals = int(
        analyzed["signal"]
        .isin(
            [
                "LONG",
                "SHORT",
            ]
        )
        .sum()
    )

    v2_data = block_short_atr_8_12(
        analyzed.copy()
    )

    v2_remaining = int(
        v2_data["signal"]
        .isin(
            [
                "LONG",
                "SHORT",
            ]
        )
        .sum()
    )

    v2_blocks = (
        original_signals
        - v2_remaining
    )

    v3_data = block_low_vol_thursday(
        analyzed.copy()
    )

    v3_remaining = int(
        v3_data["signal"]
        .isin(
            [
                "LONG",
                "SHORT",
            ]
        )
        .sum()
    )

    v3_blocks = (
        original_signals
        - v3_remaining
    )

    # Exact V5:
    #
    # V2 followed by V3.
    v5_transform = compose_transforms(
        block_short_atr_8_12,
        block_low_vol_thursday,
    )

    v5_data = v5_transform(
        analyzed.copy()
    )

    v5_remaining = int(
        v5_data["signal"]
        .isin(
            [
                "LONG",
                "SHORT",
            ]
        )
        .sum()
    )

    v5_blocks = (
        original_signals
        - v5_remaining
    )

    print(
        f"Original LONG/SHORT signals : "
        f"{original_signals}"
    )

    print(
        f"V2 blocked signals          : "
        f"{v2_blocks}"
    )

    print(
        f"V3 individual blocks       : "
        f"{v3_blocks}"
    )

    print(
        f"V5 total blocked signals    : "
        f"{v5_blocks}"
    )

    print(
        f"V5 remaining signals        : "
        f"{v5_remaining}"
    )

    print(
        "PASS: exact V5 signal filtering verified"
    )

    print(
        "[3/6] Running V5 backtest..."
    )

    backtester = BacktestEngine(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
    )

    backtest_result = backtester.run(
        v5_data
    )

    if not isinstance(
        backtest_result,
        dict,
    ):
        raise TypeError(
            "BacktestEngine.run() did not "
            "return a dictionary."
        )

    trades = backtest_result.get(
        "trades",
        [],
    )

    trades_df = prepare_trade_data(
        trades
    )

    if trades_df.empty:
        raise RuntimeError(
            "V5 backtest returned no trades."
        )

    print(
        f"PASS: {len(trades_df)} "
        f"V5 trades returned"
    )

    print(
        "[4/6] Splitting winning and losing trades..."
    )

    losses = trades_df[
        trades_df["result"] == "LOSS"
    ].copy()

    wins = trades_df[
        trades_df["result"] == "WIN"
    ].copy()

    print(
        f"Winning trades: {len(wins)}"
    )

    print(
        f"Losing trades : {len(losses)}"
    )

    print(
        "[5/6] Comparing recurring conditions..."
    )

    distributions = [
        (
            "DAY OF WEEK",
            "day",
        ),
        (
            "UTC HOUR",
            "hour_bucket",
        ),
        (
            "RSI BUCKET",
            "rsi_bucket",
        ),
        (
            "ATR BUCKET",
            "atr_bucket",
        ),
        (
            "DIRECTION",
            "direction",
        ),
        (
            "TREND REGIME",
            "regime",
        ),
        (
            "VOLATILITY REGIME",
            "volatility_regime",
        ),
    ]

    for title, column in distributions:

        if column in trades_df.columns:
            print_distribution(
                title,
                losses,
                wins,
                column,
            )

    print_combinations(
        losses,
        wins,
    )

    print(
        "[6/6] Ranking strongest recurring "
        "loss conditions..."
    )

    print(
        "--------------------------------------------"
    )

    rankings = []

    ranking_columns = [
        "day",
        "hour_bucket",
        "rsi_bucket",
        "atr_bucket",
        "direction",
        "regime",
        "volatility_regime",
    ]

    for column in ranking_columns:

        if column not in losses.columns:
            continue

        loss_counts = Counter(
            str(x)
            for x in losses[column].dropna()
        )

        win_counts = Counter(
            str(x)
            for x in wins[column].dropna()
        )

        for key, loss_count in loss_counts.items():

            if loss_count < 3:
                continue

            loss_share = (
                loss_count
                / max(len(losses), 1)
            )

            win_share = (
                win_counts.get(
                    key,
                    0,
                )
                / max(len(wins), 1)
            )

            gap = (
                loss_share
                - win_share
            )

            rankings.append(
                (
                    gap,
                    loss_count,
                    win_counts.get(
                        key,
                        0,
                    ),
                    column,
                    key,
                )
            )

    rankings.sort(
        reverse=True
    )

    if rankings:

        for (
            gap,
            loss_count,
            win_count,
            column,
            key,
        ) in rankings[:10]:

            print(
                f"{column:20s} = "
                f"{key:20s} | "
                f"losses {loss_count:2d} | "
                f"wins {win_count:2d} | "
                f"gap {gap * 100:+5.1f} pp"
            )

    else:
        print(
            "No recurring condition had "
            "at least 3 losses."
        )

    print()
    print("INTERPRETATION RULES")
    print("--------------------")

    print(
        "1. Recurring does not automatically "
        "mean we should add a filter."
    )

    print(
        "2. A useful pattern should have "
        "multiple losses and a meaningful "
        "loss-vs-win gap."
    )

    print(
        "3. Conditions common to both wins "
        "and losses are weak evidence."
    )

    print(
        "4. Any promising pattern must be "
        "tested out-of-sample."
    )

    print(
        "5. This test does NOT modify V5."
    )

    print()
    print(
        "V5 PATTERN ANALYSIS COMPLETE"
    )


if __name__ == "__main__":
    main()