from pathlib import Path
import math
import pandas as pd

from engines.pipeline import TradingPipeline
from engines.backtest import BacktestEngine


DATA_FILE = Path("data") / "xauusd" / "raw" / "XAUUSD_5m.csv"
INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
STOP_ATR_MULTIPLIER = 2.0
TAKE_PROFIT_RATIO = 2.0


def block_short_atr_8_12(df):
    result = df.copy()
    mask = (
        (result["signal"] == "SHORT")
        & (result["atr"] >= 8.0)
        & (result["atr"] < 12.0)
    )
    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = "Blocked by V5: SHORT + ATR 8-12"
    return result


def block_low_vol_thursday(df):
    result = df.copy()
    timestamp = pd.to_datetime(result["timestamp"], utc=True)
    mask = (
        result["signal"].isin(["LONG", "SHORT"])
        & (result["volatility_regime"] == "LOW_VOLATILITY")
        & (timestamp.dt.dayofweek == 3)
    )
    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = "Blocked by V5: LOW_VOLATILITY + Thursday"
    return result


def apply_v5(df):
    return block_low_vol_thursday(block_short_atr_8_12(df))


def run_backtest(df):
    engine = BacktestEngine(
        initial_balance=INITIAL_BALANCE,
        risk_per_trade=RISK_PER_TRADE,
        stop_atr_multiplier=STOP_ATR_MULTIPLIER,
        take_profit_ratio=TAKE_PROFIT_RATIO,
    )
    return engine.run(df.copy())


def as_trades(result):
    trades = result.get("trades", [])
    if isinstance(trades, pd.DataFrame):
        return trades.to_dict("records")
    return list(trades)


def trade_pnl(trade):
    try:
        return float(trade.get("pnl", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def profit_factor(trades):
    values = [trade_pnl(t) for t in trades]
    gains = sum(p for p in values if p > 0)
    losses = abs(sum(p for p in values if p < 0))
    if losses == 0:
        return math.inf if gains > 0 else 0.0
    return gains / losses


def longest_losing_streak(trades):
    longest = current = 0
    for trade in trades:
        if trade_pnl(trade) < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def side_stats(trades, side):
    selected = [
        t for t in trades
        if str(t.get("direction", "")).upper() == side
    ]
    wins = sum(1 for t in selected if trade_pnl(t) > 0)
    pnl = sum(trade_pnl(t) for t in selected)
    return {
        "count": len(selected),
        "wins": wins,
        "win_rate": wins / len(selected) if selected else 0.0,
        "pnl": pnl,
        "profit_factor": profit_factor(selected),
    }


def fmt_money(value):
    return f"{value:,.2f}"


def fmt_pf(value):
    return "∞" if math.isinf(value) else f"{value:.3f}"


def summarize(name, result):
    trades = as_trades(result)
    wins = sum(1 for t in trades if trade_pnl(t) > 0)
    losses = sum(1 for t in trades if trade_pnl(t) < 0)
    pnl_from_trades = sum(trade_pnl(t) for t in trades)

    final_balance = float(result.get("final_balance", INITIAL_BALANCE))
    balance_change = final_balance - INITIAL_BALANCE
    drawdown = float(result.get("max_drawdown", 0.0) or 0.0)

    print(f"\n{'=' * 58}")
    print(name)
    print("=" * 58)
    print(f"Trades:                  {len(trades)}")
    print(f"Winning / losing trades: {wins} / {losses}")
    print(f"Win rate:                {wins / len(trades):.2%}" if trades else "Win rate:                N/A")
    print(f"Trade P&L total:         {fmt_money(pnl_from_trades)}")
    print(f"Final balance:           {fmt_money(final_balance)}")
    print(f"Balance change:           {fmt_money(balance_change)}")
    print(f"Profit factor:            {fmt_pf(profit_factor(trades))}")
    print(f"Max drawdown:             {drawdown:.2%}")
    print(f"Longest losing streak:    {longest_losing_streak(trades)}")

    if abs(pnl_from_trades - balance_change) > 0.05:
        print(
            "WARNING: Sum of trade P&L differs from balance change. "
            "Check the backtest accounting before interpreting results."
        )

    for side in ("LONG", "SHORT"):
        stats = side_stats(trades, side)
        print(
            f"{side:5} | trades={stats['count']:3} "
            f"| wins={stats['wins']:3} "
            f"| win rate={stats['win_rate']:.2%} "
            f"| P&L={fmt_money(stats['pnl'])} "
            f"| PF={fmt_pf(stats['profit_factor'])}"
        )

    return {
        "name": name,
        "trades": len(trades),
        "pnl": pnl_from_trades,
        "final_balance": final_balance,
        "win_rate": wins / len(trades) if trades else 0.0,
        "profit_factor": profit_factor(trades),
        "max_drawdown": drawdown,
        "losing_streak": longest_losing_streak(trades),
    }


def main():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"Historical CSV not found: {DATA_FILE}")

    print("Loading historical CSV and preparing features...")
    print("This script does not intentionally write to the historical database.")
    print("No broker connection or live orders are used.")

    pipeline = TradingPipeline()
    pipeline_output = pipeline.run(DATA_FILE)
    data = pipeline_output.get("data")

    if data is None or data.empty:
        raise RuntimeError("Pipeline returned no analyzed data.")

    if not {"signal", "atr", "timestamp", "volatility_regime"}.issubset(data.columns):
        raise RuntimeError(
            "Analyzed data is missing columns required for the V5 filters."
        )

    original_signals = int(data["signal"].isin(["LONG", "SHORT"]).sum())
    v5_data = apply_v5(data)
    remaining_signals = int(v5_data["signal"].isin(["LONG", "SHORT"]).sum())
    blocked_signals = original_signals - remaining_signals

    print(f"\nAnalyzed rows:        {len(data):,}")
    print(f"Baseline signals:     {original_signals}")
    print(f"V5 blocked signals:   {blocked_signals}")
    print(f"V5 remaining signals: {remaining_signals}")

    if len(data) != 36006 or original_signals != 471:
        raise RuntimeError(
            "Dataset or baseline signal count differs from the previously checked data. "
            "Stopping to avoid an unreliable comparison."
        )

    if blocked_signals != 189 or remaining_signals != 282:
        raise RuntimeError(
            "V5 filter counts differ from previous results. "
            "Stopping to avoid an unreliable comparison."
        )

    print("\nRunning baseline backtest...")
    baseline_result = run_backtest(data)

    print("Running V5 backtest...")
    v5_result = run_backtest(v5_data)

    baseline = summarize("BASELINE", baseline_result)
    v5 = summarize("EXPERIMENT V5", v5_result)

    print(f"\n{'=' * 58}")
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 58)
    print(f"{'Metric':<24}{'Baseline':>16}{'V5':>16}")
    print("-" * 56)
    print(f"{'Trades':<24}{baseline['trades']:>16}{v5['trades']:>16}")
    print(
        f"{'Trade P&L':<24}"
        f"{fmt_money(baseline['pnl']):>16}"
        f"{fmt_money(v5['pnl']):>16}"
    )
    print(
        f"{'Final balance':<24}"
        f"{fmt_money(baseline['final_balance']):>16}"
        f"{fmt_money(v5['final_balance']):>16}"
    )
    print(
        f"{'Win rate':<24}"
        f"{baseline['win_rate']:>15.2%}"
        f"{v5['win_rate']:>15.2%}"
    )
    print(
        f"{'Profit factor':<24}"
        f"{fmt_pf(baseline['profit_factor']):>16}"
        f"{fmt_pf(v5['profit_factor']):>16}"
    )
    print(
        f"{'Max drawdown':<24}"
        f"{baseline['max_drawdown']:>15.2%}"
        f"{v5['max_drawdown']:>15.2%}"
    )
    print(
        f"{'Longest losing streak':<24}"
        f"{baseline['losing_streak']:>16}"
        f"{v5['losing_streak']:>16}"
    )

    print("\nComparison finished. No result file was intentionally created.")
    print("Historical simulation only; this does not establish live profitability.")


if __name__ == "__main__":
    main()
