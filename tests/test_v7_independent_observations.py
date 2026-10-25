from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from engines.paper_runner import PaperTradingRunner
import tempfile
from engines.paper_persistence import PaperPersistence


# ============================================================
# Paths / constants
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "xauusd"
    / "raw"
    / "XAUUSD_5m.csv"
)

STRATEGY_NAME = "XAUUSD_V7_PAPER_TEST"

OBSERVATION_COUNT = 4
WARMUP_DAYS = 7


# ============================================================
# V7 rules
# ============================================================

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
        "Blocked by V7: SHORT + ATR 8-12"
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
        & (result["volatility_regime"] == "LOW_VOLATILITY")
        & (timestamp.dt.dayofweek == 3)
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by V7: LOW_VOLATILITY + Thursday"
    )

    return result


def block_tuesday_wednesday(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    timestamp = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    mask = (
        result["signal"].isin(["LONG", "SHORT"])
        & timestamp.dt.dayofweek.isin([1, 2])
    )

    result.loc[mask, "signal"] = "NO_SIGNAL"
    result.loc[mask, "signal_strength"] = 0.0
    result.loc[mask, "signal_reason"] = (
        "Blocked by V7: Tuesday/Wednesday"
    )

    return result


def v7_transform_for_window(
    df: pd.DataFrame,
    observation_start: pd.Timestamp,
) -> pd.DataFrame:
    """
    Apply the exact V7 rules, then suppress trades before the
    observation start.

    The pre-start rows are retained as indicator warm-up data.
    They are not counted as observation trades.
    """
    result = block_short_atr_8_12(df)
    result = block_low_vol_thursday(result)
    result = block_tuesday_wednesday(result)

    timestamp = pd.to_datetime(
        result["timestamp"],
        utc=True,
    )

    pre_observation = timestamp < observation_start

    result.loc[pre_observation, "signal"] = "NO_SIGNAL"
    result.loc[pre_observation, "signal_strength"] = 0.0
    result.loc[pre_observation, "signal_reason"] = (
        "Observation warm-up: signals excluded before window start"
    )

    return result


# ============================================================
# Data helpers
# ============================================================

def load_raw_data() -> pd.DataFrame:
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Raw XAUUSD file not found: {RAW_FILE}"
        )

    data = pd.read_csv(RAW_FILE)

    if "datetime" not in data.columns:
        raise ValueError(
            "Expected raw CSV column 'datetime' was not found."
        )

    data["datetime"] = pd.to_datetime(
        data["datetime"],
        utc=True,
        errors="coerce",
    )

    data = data.dropna(
        subset=["datetime"]
    )

    data = data.sort_values(
        "datetime"
    ).reset_index(drop=True)

    if data.empty:
        raise ValueError(
            "Raw XAUUSD dataset is empty after timestamp parsing."
        )

    return data


def build_observation_windows(
    data: pd.DataFrame,
    count: int,
):
    """
    Split the available chronological period into equal time
    windows. Each window receives a small historical warm-up
    before its start so technical indicators have context.

    The observation itself begins exactly at observation_start.
    """
    start = data["datetime"].min()
    end = data["datetime"].max()

    total_span = end - start

    windows = []

    for index in range(count):
        window_start = start + (
            total_span * index / count
        )

        if index == count - 1:
            window_end = end
        else:
            window_end = start + (
                total_span * (index + 1) / count
            )

        warmup_start = max(
            start,
            window_start - pd.Timedelta(
                days=WARMUP_DAYS
            ),
        )

        window_data = data.loc[
            (data["datetime"] >= warmup_start)
            & (data["datetime"] <= window_end)
        ].copy()

        windows.append(
            {
                "number": index + 1,
                "observation_start": window_start,
                "observation_end": window_end,
                "warmup_start": warmup_start,
                "data": window_data,
            }
        )

    return windows


def save_window_csv(
    window,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    window["data"].to_csv(
        output_path,
        index=False,
    )


# ============================================================
# Main
# ============================================================

def main() -> None:
    print()
    print("=" * 80)
    print("V7 INDEPENDENT PAPER OBSERVATION RUNNER")
    print("=" * 80)
    print()
    print("This test:")
    print("- keeps the exact V7 strategy rules")
    print("- uses different chronological observation windows")
    print("- keeps warm-up data for technical indicators")
    print("- excludes warm-up trades from each observation")
    print("- runs PAPER mode only")
    print("- does not place live orders")
    print()

    raw = load_raw_data()

    print(
        f"Raw rows      : {len(raw):,}"
    )
    print(
        f"Dataset start : {raw['datetime'].min()}"
    )
    print(
        f"Dataset end   : {raw['datetime'].max()}"
    )
    print()

    windows = build_observation_windows(
        raw,
        OBSERVATION_COUNT,
    )

    results = []

    observation_dir = (
        Path(tempfile.mkdtemp(prefix="v7_observations_"))
    )


    for window in windows:
        number = window["number"]
        observation_start = window["observation_start"]
        observation_end = window["observation_end"]

        output_file = (
            observation_dir
            / f"V7_observation_{number}.csv"
        )

        print()
        print("-" * 80)
        print(
            f"OBSERVATION {number}/{OBSERVATION_COUNT}"
        )
        print("-" * 80)
        print(
            f"Warm-up start     : "
            f"{window['warmup_start']}"
        )
        print(
            f"Observation start : "
            f"{observation_start}"
        )
        print(
            f"Observation end   : "
            f"{observation_end}"
        )
        print(
            f"Rows supplied     : "
            f"{len(window['data']):,}"
        )

        save_window_csv(
            window,
            output_file,
        )

        def observation_transform(
            df,
            start=observation_start,
        ):
            return v7_transform_for_window(
                df,
                start,
            )

        runner = PaperTradingRunner(
            initial_balance=10_000.0,
            strategy_name=STRATEGY_NAME,
            persistence=PaperPersistence(
                observation_dir / "v7_observations_test.db"
            ),
            session_metadata={
                "observation_type": (
                    "V7_INDEPENDENT_CHRONOLOGICAL"
                ),
                "observation_number": number,
                "observation_start": (
                    str(observation_start)
                ),
                "observation_end": (
                    str(observation_end)
                ),
                "warmup_start": (
                    str(window["warmup_start"])
                ),
                "warmup_days": WARMUP_DAYS,
            },
        )

        result = runner.run(
            str(output_file),
            strategy_transform=observation_transform,
        )

        paper = result.get(
            "paper_report",
            result.get(
                "paper",
                result,
            ),
        )

        results.append(
            {
                "number": number,
                "start": observation_start,
                "end": observation_end,
                "result": result,
            }
        )

        print()
        print(
            f"Observation {number} completed."
        )

        if isinstance(paper, dict):
            account = paper.get("account", {})
            performance = paper.get("performance", {})

            print(
                f"Final balance : "
                f"{account.get('final_balance', 'N/A')}"
            )
            print(
                f"P&L           : "
                f"{performance.get('total_pnl', 'N/A')}"
            )
            print(
                f"Trades        : "
                f"{performance.get('trades', 'N/A')}"
            )
            print(
                f"Win rate      : "
                f"{performance.get('win_rate', 'N/A')}"
            )
            print(
                f"Profit factor : "
                f"{performance.get('profit_factor', 'N/A')}"
            )
            print(
                f"Max drawdown  : "
                f"{account.get('max_drawdown', 'N/A')}"
            )

    print()
    print("=" * 80)
    print("INDEPENDENT OBSERVATION RUNS COMPLETE")
    print("=" * 80)
    print()
    print(
        f"Created {len(results)} chronological V7 paper sessions."
    )
    print()
    print(
        "Now run the existing observation analyzer:"
    )
    print()
    print(
        "python -m tests.test_v7_paper_observation"
    )
    print()
    print(
        "The analyzer should now distinguish sessions by their "
        "different trade histories."
    )
    print()
    print(
        "Do not promote V7 yet. First inspect how many runs are "
        "actually unique and how their performance differs."
    )


if __name__ == "__main__":
    main()

