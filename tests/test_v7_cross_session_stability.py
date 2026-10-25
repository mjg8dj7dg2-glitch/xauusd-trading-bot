from __future__ import annotations

import contextlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd

from engines.paper_runner import PaperTradingRunner


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "xauusd" / "paper_observations"


# ============================================================
# OBSERVATION WINDOWS
#
# The CSV files contain warm-up rows before the actual
# observation period. These timestamps define when each
# independent observation officially begins.
# ============================================================

OBSERVATIONS = {
    1: {
        "file": DATA_DIR / "V7_observation_1.csv",
        "start": "2026-03-23 02:30:00+00:00",
    },
    2: {
        "file": DATA_DIR / "V7_observation_2.csv",
        "start": "2026-05-08 02:22:30+00:00",
    },
    3: {
        "file": DATA_DIR / "V7_observation_3.csv",
        "start": "2026-06-23 02:15:00+00:00",
    },
    4: {
        "file": DATA_DIR / "V7_observation_4.csv",
        "start": "2026-08-08 02:07:30+00:00",
    },
}


# ============================================================
# METRICS
# ============================================================

@dataclass
class Metrics:
    session: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    pf: float
    pnl: float
    max_dd: float
    health: str


# ============================================================
# TIMESTAMP HELPER
# ============================================================

def get_timestamp_series(df: pd.DataFrame) -> pd.Series:
    if "timestamp" in df.columns:
        column = "timestamp"
    elif "datetime" in df.columns:
        column = "datetime"
    else:
        raise ValueError(
            "DataFrame must contain either 'timestamp' or 'datetime'."
        )

    return pd.to_datetime(df[column], utc=True)


# ============================================================
# V5 TRANSFORM
#
# V5 =
#   1. Block SHORT when ATR is 8 <= ATR < 12
#   2. Block LOW_VOLATILITY Thursday signals
#   3. Block all warm-up-period signals
# ============================================================

def v5_transform(
    df: pd.DataFrame,
    observation_start: str,
) -> pd.DataFrame:

    result = df.copy()

    if "signal" not in result.columns:
        return result

    # --------------------------------------------------------
    # V2 rule:
    # Block SHORT signals when ATR is 8 <= ATR < 12
    # --------------------------------------------------------

    if "atr" in result.columns:
        mask_short_atr = (
            (result["signal"] == "SHORT")
            & (result["atr"] >= 8.0)
            & (result["atr"] < 12.0)
        )

        result.loc[mask_short_atr, "signal"] = "NO_SIGNAL"

    # --------------------------------------------------------
    # V3 rule:
    # Block LOW_VOLATILITY Thursday signals
    # --------------------------------------------------------

    if "volatility_regime" in result.columns:
        timestamp = get_timestamp_series(result)

        mask_low_vol_thursday = (
            result["signal"].isin(["LONG", "SHORT"])
            & (result["volatility_regime"] == "LOW_VOLATILITY")
            & (timestamp.dt.dayofweek == 3)
        )

        result.loc[mask_low_vol_thursday, "signal"] = "NO_SIGNAL"

    # --------------------------------------------------------
    # IMPORTANT:
    # Do not allow warm-up rows to create observation trades.
    # --------------------------------------------------------

    timestamp = get_timestamp_series(result)
    observation_start_ts = pd.Timestamp(
        observation_start,
        tz="UTC",
    )

    warmup_mask = timestamp < observation_start_ts

    result.loc[warmup_mask, "signal"] = "NO_SIGNAL"

    return result


# ============================================================
# V7 TRANSFORM
#
# V7 =
#   V5
#   +
#   block LONG/SHORT signals Tuesday and Wednesday
#   +
#   block warm-up signals
# ============================================================

def v7_transform(
    df: pd.DataFrame,
    observation_start: str,
) -> pd.DataFrame:

    result = v5_transform(
        df,
        observation_start,
    )

    if "signal" not in result.columns:
        return result

    timestamp = get_timestamp_series(result)

    # --------------------------------------------------------
    # V7 additional rule:
    # Block Tuesday and Wednesday LONG/SHORT signals
    # --------------------------------------------------------

    mask_tuesday_wednesday = (
        result["signal"].isin(["LONG", "SHORT"])
        & timestamp.dt.dayofweek.isin([1, 2])
    )

    result.loc[
        mask_tuesday_wednesday,
        "signal",
    ] = "NO_SIGNAL"

    return result


# ============================================================
# PAPER RUNNER SUMMARY PARSER
#
# IMPORTANT:
# We intentionally parse the runner's printed
# "PAPER TRADING SUMMARY".
#
# The previous version recursively searched dictionaries and
# accidentally selected another nested metrics object.
# ============================================================

SUMMARY_PATTERN = re.compile(
    r"PAPER TRADING SUMMARY.*?"
    r"Final balance\s+([0-9,.\-]+).*?"
    r"P&L\s+([+\-0-9,.\-]+).*?"
    r"Max DD\s+([0-9,.\-]+)%.*?"
    r"Trades\s+(\d+).*?"
    r"Wins\s+(\d+).*?"
    r"Losses\s+(\d+).*?"
    r"Win rate\s+([0-9,.\-]+)%.*?"
    r"PF\s+([0-9,.\-]+).*?"
    r"Paper health\s+([A-Z_]+)",
    re.S,
)


def parse_runner_summary(
    output: str,
    session_name: str,
) -> Metrics:

    match = SUMMARY_PATTERN.search(output)

    if not match:
        raise RuntimeError(
            "Could not find the authoritative PAPER TRADING SUMMARY "
            "in PaperTradingRunner output.\n\n"
            "Last 6000 characters of output:\n"
            + output[-6000:]
        )

    (
        final_balance,
        pnl,
        max_dd,
        trades,
        wins,
        losses,
        win_rate,
        pf,
        health,
    ) = match.groups()

    # final_balance is parsed to verify that the runner summary
    # was found, but P&L is taken directly from the runner.
    _ = final_balance

    return Metrics(
        session=session_name,
        trades=int(trades),
        wins=int(wins),
        losses=int(losses),
        win_rate=float(
            win_rate.replace(",", "")
        ),
        pf=float(
            pf.replace(",", "")
        ),
        pnl=float(
            pnl.replace(",", "")
        ),
        max_dd=float(
            max_dd.replace(",", "")
        ),
        health=health,
    )


# ============================================================
# RUN ONE OBSERVATION
# ============================================================

def run_one(
    variant: str,
    observation_number: int,
) -> Metrics:

    specification = OBSERVATIONS[
        observation_number
    ]

    data_file = specification["file"]
    observation_start = specification["start"]

    if not data_file.exists():
        raise FileNotFoundError(
            f"Observation file does not exist:\n{data_file}"
        )

    if variant == "V7":

        transform: Callable[
            [pd.DataFrame],
            pd.DataFrame,
        ] = lambda df: v7_transform(
            df,
            observation_start,
        )

    elif variant == "V5":

        transform = lambda df: v5_transform(
            df,
            observation_start,
        )

    else:
        raise ValueError(
            f"Unknown strategy variant: {variant}"
        )

    strategy_name = (
        f"XAUUSD_{variant}_"
        f"STABILITY_FIXED_{observation_number}"
    )

    runner = PaperTradingRunner(
        initial_balance=10000.0,
        strategy_name=strategy_name,
    )

    # Capture the runner's printed summary.
    captured_output = io.StringIO()

    with contextlib.redirect_stdout(
        captured_output
    ):

        runner.run(
            str(data_file),
            strategy_transform=transform,
        )

    output = captured_output.getvalue()

    # Show the real runner output to the user.
    print(output)

    return parse_runner_summary(
        output,
        f"OBS_{observation_number}",
    )


# ============================================================
# AGGREGATION
# ============================================================

def aggregate(
    rows: list[Metrics],
) -> dict:

    trades = sum(
        row.trades
        for row in rows
    )

    wins = sum(
        row.wins
        for row in rows
    )

    losses = sum(
        row.losses
        for row in rows
    )

    pnl = sum(
        row.pnl
        for row in rows
    )

    positive_sessions = sum(
        row.pnl > 0
        for row in rows
    )

    worst_drawdown = max(
        (
            row.max_dd
            for row in rows
        ),
        default=0.0,
    )

    win_rate = (
        wins / trades * 100.0
        if trades
        else 0.0
    )

    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "pnl": pnl,
        "positive_sessions": positive_sessions,
        "worst_drawdown": worst_drawdown,
    }


# ============================================================
# PRINT TABLE
# ============================================================

def print_table(
    title: str,
    rows: list[Metrics],
) -> None:

    print()
    print(title)
    print("-" * 120)

    print(
        f"{'Session':<10}"
        f"{'Trades':>9}"
        f"{'Wins':>8}"
        f"{'Losses':>9}"
        f"{'Win%':>10}"
        f"{'PF':>10}"
        f"{'P&L':>14}"
        f"{'Max DD':>10}"
        f"{'Health':>24}"
    )

    for row in rows:

        print(
            f"{row.session:<10}"
            f"{row.trades:>9}"
            f"{row.wins:>8}"
            f"{row.losses:>9}"
            f"{row.win_rate:>9.2f}%"
            f"{row.pf:>10.4f}"
            f"{row.pnl:>14.2f}"
            f"{row.max_dd:>9.2f}%"
            f"{row.health:>24}"
        )


# ============================================================
# LEAVE-ONE-OUT ANALYSIS
# ============================================================

def print_leave_one_out(
    rows: list[Metrics],
    label: str,
) -> None:

    print()
    print(label)
    print("-" * 120)

    for index, removed in enumerate(rows):

        remaining = [
            row
            for j, row in enumerate(rows)
            if j != index
        ]

        summary = aggregate(
            remaining
        )

        print(
            f"Remove {removed.session}: "
            f"trades={summary['trades']}, "
            f"WR={summary['win_rate']:.2f}%, "
            f"P&L={summary['pnl']:+.2f}, "
            f"positive={summary['positive_sessions']}/3, "
            f"worst DD={summary['worst_drawdown']:.2f}%"
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 120)
    print("V7 CROSS-SESSION STABILITY ANALYSIS — FIXED")
    print("=" * 120)

    print()
    print("Analysis-only. No live trading.")
    print()
    print(
        "This version uses the PaperTradingRunner's "
        "PAPER TRADING SUMMARY as the authoritative metrics source."
    )
    print(
        "It also blocks all warm-up-period signals before "
        "each observation's true start."
    )
    print()

    v7_results: list[Metrics] = []
    v5_results: list[Metrics] = []

    # --------------------------------------------------------
    # Run all four observations.
    # --------------------------------------------------------

    for observation_number in OBSERVATIONS:

        print()
        print("=" * 120)
        print(
            f"OBSERVATION {observation_number}"
        )
        print("=" * 120)

        print()
        print(
            f"Running V7 — observation "
            f"{observation_number}"
        )

        v7_result = run_one(
            "V7",
            observation_number,
        )

        v7_results.append(
            v7_result
        )

        print()
        print(
            f"Running V5 — observation "
            f"{observation_number}"
        )

        v5_result = run_one(
            "V5",
            observation_number,
        )

        v5_results.append(
            v5_result
        )

    # --------------------------------------------------------
    # Window tables.
    # --------------------------------------------------------

    print_table(
        "V7 — SAME FOUR CHRONOLOGICAL WINDOWS",
        v7_results,
    )

    print_table(
        "V5 — SAME FOUR CHRONOLOGICAL WINDOWS",
        v5_results,
    )

    # --------------------------------------------------------
    # Aggregate.
    # --------------------------------------------------------

    v7_aggregate = aggregate(
        v7_results
    )

    v5_aggregate = aggregate(
        v5_results
    )

    print()
    print("=" * 120)
    print("CROSS-SESSION AGGREGATE")
    print("=" * 120)

    print(
        f"V7: "
        f"trades={v7_aggregate['trades']}, "
        f"wins={v7_aggregate['wins']}, "
        f"losses={v7_aggregate['losses']}, "
        f"WR={v7_aggregate['win_rate']:.2f}%, "
        f"P&L={v7_aggregate['pnl']:+.2f}, "
        f"positive sessions="
        f"{v7_aggregate['positive_sessions']}/4, "
        f"worst session DD="
        f"{v7_aggregate['worst_drawdown']:.2f}%"
    )

    print(
        f"V5: "
        f"trades={v5_aggregate['trades']}, "
        f"wins={v5_aggregate['wins']}, "
        f"losses={v5_aggregate['losses']}, "
        f"WR={v5_aggregate['win_rate']:.2f}%, "
        f"P&L={v5_aggregate['pnl']:+.2f}, "
        f"positive sessions="
        f"{v5_aggregate['positive_sessions']}/4, "
        f"worst session DD="
        f"{v5_aggregate['worst_drawdown']:.2f}%"
    )

    # --------------------------------------------------------
    # V7 leave-one-out.
    # --------------------------------------------------------

    print_leave_one_out(
        v7_results,
        "V7 LEAVE-ONE-SESSION-OUT",
    )

    # --------------------------------------------------------
    # V5 leave-one-out.
    # --------------------------------------------------------

    print_leave_one_out(
        v5_results,
        "V5 LEAVE-ONE-SESSION-OUT",
    )

    # --------------------------------------------------------
    # Best/worst V7 sensitivity.
    # --------------------------------------------------------

    best_v7 = max(
        v7_results,
        key=lambda row: row.pnl,
    )

    worst_v7 = min(
        v7_results,
        key=lambda row: row.pnl,
    )

    without_best = [
        row
        for row in v7_results
        if row is not best_v7
    ]

    without_worst = [
        row
        for row in v7_results
        if row is not worst_v7
    ]

    without_best_summary = aggregate(
        without_best
    )

    without_worst_summary = aggregate(
        without_worst
    )

    print()
    print("=" * 120)
    print("V7 BEST/WORST SESSION SENSITIVITY")
    print("=" * 120)

    print(
        f"Best session : "
        f"{best_v7.session} | "
        f"P&L={best_v7.pnl:+.2f}"
    )

    print(
        f"Worst session: "
        f"{worst_v7.session} | "
        f"P&L={worst_v7.pnl:+.2f}"
    )

    print(
        f"Without best : "
        f"trades={without_best_summary['trades']}, "
        f"WR={without_best_summary['win_rate']:.2f}%, "
        f"P&L={without_best_summary['pnl']:+.2f}, "
        f"positive="
        f"{without_best_summary['positive_sessions']}/3"
    )

    print(
        f"Without worst: "
        f"trades={without_worst_summary['trades']}, "
        f"WR={without_worst_summary['win_rate']:.2f}%, "
        f"P&L={without_worst_summary['pnl']:+.2f}, "
        f"positive="
        f"{without_worst_summary['positive_sessions']}/3"
    )

    # --------------------------------------------------------
    # V7 vs V5.
    # --------------------------------------------------------

    print()
    print("=" * 120)
    print("V7 VS V5 — WINDOW-BY-WINDOW CHANGE")
    print("=" * 120)

    print(
        f"{'Session':<10}"
        f"{'Delta Trades':>15}"
        f"{'Delta Win%':>15}"
        f"{'Delta PF':>12}"
        f"{'Delta P&L':>15}"
        f"{'Delta DD':>12}"
    )

    for v7, v5 in zip(
        v7_results,
        v5_results,
    ):

        print(
            f"{v7.session:<10}"
            f"{v7.trades - v5.trades:>15}"
            f"{v7.win_rate - v5.win_rate:>14.2f}pp"
            f"{v7.pf - v5.pf:>12.4f}"
            f"{v7.pnl - v5.pnl:>15.2f}"
            f"{v7.max_dd - v5.max_dd:>11.2f}pp"
        )

    # --------------------------------------------------------
    # Decision guide.
    # --------------------------------------------------------

    print()
    print("=" * 120)
    print("DECISION GUIDE")
    print("=" * 120)

    print(
        "This is a paper/backtest stability gate, "
        "not live-trading authorization."
    )

    print(
        "The important checks are:"
    )

    print(
        "1. V7 remains profitable across the chronological windows."
    )

    print(
        "2. V7 remains profitable after removing its best window."
    )

    print(
        "3. V7 maintains a meaningful advantage over V5."
    )

    print(
        "4. The smallest-trade-count window is treated as "
        "weaker evidence rather than being over-weighted."
    )

    print(
        "5. No automatic promotion to active trading is performed "
        "by this test."
    )

    print()
    print("STABILITY TEST COMPLETE.")


if __name__ == "__main__":
    main()