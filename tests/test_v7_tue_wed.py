from pathlib import Path

import pandas as pd

from engines.backtest import BacktestEngine
from engines.pipeline import TradingPipeline
from engines.strategy_experiment import (
    block_low_vol_thursday,
    block_short_atr_8_12,
    compose_transforms,
)


DATA_FILE = Path("data") / "xauusd" / "raw" / "XAUUSD_5m.csv"


def block_tuesday_wednesday(data):
    """
    Block LONG/SHORT signals occurring on Tuesday or Wednesday.

    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    """
    result = data.copy()

    timestamps = pd.to_datetime(
        result["timestamp"],
        errors="coerce",
        utc=True,
    )

    blocked = (
        result["signal"].isin(["LONG", "SHORT"])
        & timestamps.dt.dayofweek.isin([1, 2])
    )

    result.loc[blocked, "signal"] = "NO_SIGNAL"

    return result


def run_backtest(data):
    engine = BacktestEngine(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
    )

    return engine.run(data)


def summarize(name, result):
    trades = result.get("trades", [])

    wins = sum(
        1
        for trade in trades
        if trade.get("result") == "WIN"
    )

    losses = sum(
        1
        for trade in trades
        if trade.get("result") == "LOSS"
    )

    pnl = sum(
        float(trade.get("pnl", 0.0))
        for trade in trades
    )

    gross_profit = sum(
        float(trade.get("pnl", 0.0))
        for trade in trades
        if float(trade.get("pnl", 0.0)) > 0
    )

    gross_loss = abs(
        sum(
            float(trade.get("pnl", 0.0))
            for trade in trades
            if float(trade.get("pnl", 0.0)) < 0
        )
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else float("inf")
    )

    win_rate = (
        wins / len(trades)
        if trades
        else 0.0
    )

    max_drawdown = float(
        result.get("max_drawdown_pct", 0.0)
    )

    return {
        "name": name,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "pnl": pnl,
        "max_drawdown_pct": max_drawdown,
    }


def print_summary(summary):
    print(f"\n{summary['name']}")
    print("-" * len(summary["name"]))
    print(f"Trades        : {summary['trades']}")
    print(f"Wins          : {summary['wins']}")
    print(f"Losses        : {summary['losses']}")
    print(f"Win rate      : {summary['win_rate']:.2%}")
    print(f"Profit factor : {summary['profit_factor']:.4f}")
    print(f"P&L           : {summary['pnl']:+,.2f}")
    print(f"Max drawdown  : {summary['max_drawdown_pct']:.2f}%")


def main():
    print("V7 TUESDAY/WEDNESDAY EXPERIMENT")
    print("=" * 40)

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Market data file not found: {DATA_FILE}"
        )

    print("\n[1/6] Loading and analyzing XAUUSD data...")

    pipeline = TradingPipeline()
    pipeline_report = pipeline.run(str(DATA_FILE))

    analyzed = pipeline_report["data"]

    print(f"PASS: {len(analyzed):,} rows analyzed")

    print("\n[2/6] Applying exact V5 rules...")

    # compose_transforms accepts exactly two transforms.
    # First compose the existing V5 rules.
    v5_transform = compose_transforms(
        block_short_atr_8_12,
        block_low_vol_thursday,
    )

    v5_data = v5_transform(analyzed)

    original_signals = int(
        analyzed["signal"].isin(["LONG", "SHORT"]).sum()
    )

    v5_signals = int(
        v5_data["signal"].isin(["LONG", "SHORT"]).sum()
    )

    v5_blocked = original_signals - v5_signals

    print(f"Original LONG/SHORT signals : {original_signals}")
    print(f"V5 blocked signals          : {v5_blocked}")
    print(f"V5 remaining signals        : {v5_signals}")

    print("\n[3/6] Creating V7...")

    # V7 = V5 + Tuesday/Wednesday filter.
    # Apply the new filter to the already-filtered V5 data.
    v7_data = block_tuesday_wednesday(v5_data)

    v7_signals = int(
        v7_data["signal"].isin(["LONG", "SHORT"]).sum()
    )

    v7_blocked = original_signals - v7_signals

    additional_blocked = v5_signals - v7_signals

    print(f"V7 blocked signals          : {v7_blocked}")
    print(f"V7 remaining signals        : {v7_signals}")
    print(
        "Additional signals blocked "
        f"by Tuesday/Wednesday rule : {additional_blocked}"
    )

    print("\n[4/6] Running V5 backtest...")

    v5_result = run_backtest(v5_data)
    v5_summary = summarize("V5_BASELINE", v5_result)

    print("PASS: V5 backtest completed")

    print("\n[5/6] Running V7 backtest...")

    v7_result = run_backtest(v7_data)
    v7_summary = summarize("V7_V5_PLUS_TUE_WED", v7_result)

    print("PASS: V7 backtest completed")

    print("\n[6/6] Comparing results...")

    print_summary(v5_summary)
    print_summary(v7_summary)

    print("\nCOMPARISON")
    print("----------")

    trade_change = (
        v7_summary["trades"]
        - v5_summary["trades"]
    )

    pnl_change = (
        v7_summary["pnl"]
        - v5_summary["pnl"]
    )

    pf_change = (
        v7_summary["profit_factor"]
        - v5_summary["profit_factor"]
    )

    dd_change = (
        v7_summary["max_drawdown_pct"]
        - v5_summary["max_drawdown_pct"]
    )

    win_rate_change = (
        v7_summary["win_rate"]
        - v5_summary["win_rate"]
    )

    print(f"Trade count change : {trade_change:+d}")
    print(f"P&L change         : {pnl_change:+,.2f}")
    print(f"PF change          : {pf_change:+.4f}")
    print(f"Win-rate change    : {win_rate_change:+.2%}")
    print(
        "Drawdown change    : "
        f"{dd_change:+.2f} percentage points"
    )

    print("\nDECISION CHECK")
    print("--------------")

    if v7_summary["pnl"] > v5_summary["pnl"]:
        print("V7 P&L: IMPROVED")
    else:
        print("V7 P&L: NOT IMPROVED")

    if v7_summary["profit_factor"] > v5_summary["profit_factor"]:
        print("V7 profit factor: IMPROVED")
    else:
        print("V7 profit factor: NOT IMPROVED")

    if v7_summary["max_drawdown_pct"] < v5_summary["max_drawdown_pct"]:
        print("V7 drawdown: IMPROVED")
    else:
        print("V7 drawdown: NOT IMPROVED")

    if v7_summary["win_rate"] > v5_summary["win_rate"]:
        print("V7 win rate: IMPROVED")
    else:
        print("V7 win rate: NOT IMPROVED")

    print("\nIMPORTANT")
    print("---------")
    print("This is NOT a promotion decision.")
    print("V7 must pass out-of-sample and walk-forward testing.")
    print("No production strategy has been changed.")

    print("\nV7 TUESDAY/WEDNESDAY EXPERIMENT COMPLETE")


if __name__ == "__main__":
    main()