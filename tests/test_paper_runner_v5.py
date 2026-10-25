from __future__ import annotations

from pathlib import Path

import pandas as pd

from engines.paper_runner import PaperTradingRunner
from engines.pipeline import TradingPipeline
from engines.strategy_experiment import (
    block_low_vol_thursday,
    block_short_atr_8_12,
    compose_transforms,
)


DATA_FILE = (
    Path("data")
    / "xauusd"
    / "raw"
    / "XAUUSD_5m.csv"
)

STRATEGY_NAME = "XAUUSD_PAPER_V5"


# ============================================================
# Exact V5 strategy transform
# ============================================================

v5_transform = compose_transforms(
    block_short_atr_8_12,
    block_low_vol_thursday,
)


# ============================================================
# Helpers
# ============================================================

def count_trade_signals(data: pd.DataFrame) -> int:
    if "signal" not in data.columns:
        return 0

    return int(
        data["signal"]
        .astype(str)
        .str.upper()
        .isin(["LONG", "SHORT"])
        .sum()
    )


def count_blocked_signals(
    original: pd.DataFrame,
    transformed: pd.DataFrame,
) -> int:
    original_signals = (
        original["signal"]
        .astype(str)
        .str.upper()
        .isin(["LONG", "SHORT"])
    )

    transformed_signals = (
        transformed["signal"]
        .astype(str)
        .str.upper()
        .isin(["LONG", "SHORT"])
    )

    return int(
        (
            original_signals
            & ~transformed_signals
        ).sum()
    )


def calculate_v2_blocks(
    data: pd.DataFrame,
) -> int:
    signal = (
        data["signal"]
        .astype(str)
        .str.upper()
    )

    mask = (
        (signal == "SHORT")
        & (data["atr"] >= 8.0)
        & (data["atr"] < 12.0)
    )

    return int(mask.sum())


def calculate_v3_blocks(
    data: pd.DataFrame,
) -> int:
    signal = (
        data["signal"]
        .astype(str)
        .str.upper()
    )

    timestamp = pd.to_datetime(
        data["timestamp"],
        utc=True,
        errors="coerce",
    )

    mask = (
        signal.isin(["LONG", "SHORT"])
        & (
            data["volatility_regime"]
            .astype(str)
            .str.upper()
            == "LOW_VOLATILITY"
        )
        & timestamp.dt.dayofweek.eq(3)
    )

    return int(mask.sum())


# ============================================================
# Test
# ============================================================

def main() -> None:
    print()
    print("=" * 80)
    print("PAPER TRADING V5 TEST")
    print("=" * 80)

    assert DATA_FILE.exists(), (
        f"Market data file was not found: {DATA_FILE}"
    )

    # --------------------------------------------------------
    # 1. Run the normal analysis pipeline.
    # --------------------------------------------------------

    print()
    print("[1/5] Running market analysis pipeline...")

    pipeline = TradingPipeline()

    pipeline_result = pipeline.run(
        DATA_FILE
    )

    analyzed_data = pipeline_result["data"]

    assert isinstance(
        analyzed_data,
        pd.DataFrame,
    ), "Pipeline did not return a DataFrame."

    assert len(analyzed_data) > 0, (
        "Pipeline returned no market data."
    )

    print(
        f"PASS: pipeline analyzed "
        f"{len(analyzed_data):,} rows"
    )

    # --------------------------------------------------------
    # 2. Verify the exact experiment conditions.
    # --------------------------------------------------------

    print()
    print("[2/5] Verifying exact V5 experiment rules...")

    required_columns = {
        "signal",
        "atr",
        "volatility_regime",
        "timestamp",
    }

    missing = (
        required_columns
        - set(analyzed_data.columns)
    )

    assert not missing, (
        "Missing required experiment columns: "
        + ", ".join(sorted(missing))
    )

    original_signal_count = count_trade_signals(
        analyzed_data
    )

    v2_blocks = calculate_v2_blocks(
        analyzed_data
    )

    v3_blocks = calculate_v3_blocks(
        analyzed_data
    )

    transformed_data = v5_transform(
        analyzed_data.copy()
    )

    total_v5_blocks = count_blocked_signals(
        analyzed_data,
        transformed_data,
    )

    transformed_signal_count = count_trade_signals(
        transformed_data
    )

    print(
        f"Original LONG/SHORT signals: "
        f"{original_signal_count}"
    )

    print(
        f"V2 blocks (SHORT + ATR 8-12): "
        f"{v2_blocks}"
    )

    print(
        f"V3 blocks (LOW_VOLATILITY + Thursday): "
        f"{v3_blocks}"
    )

    print(
        f"Total unique V5 blocks: "
        f"{total_v5_blocks}"
    )

    print(
        f"Signals remaining after V5: "
        f"{transformed_signal_count}"
    )

    assert total_v5_blocks > 0, (
        "V5 blocked zero signals. "
        "The experiment conditions did not "
        "match the analyzed data."
    )

    assert (
        transformed_signal_count
        == original_signal_count
        - total_v5_blocks
    ), (
        "V5 signal count does not match "
        "the number of blocked signals."
    )

    print(
        "PASS: V5 uses the exact "
        "strategy-experiment conditions"
    )

    # --------------------------------------------------------
    # 3. Run the actual persistent paper simulation.
    # --------------------------------------------------------

    print()
    print("[3/5] Running persistent V5 paper simulation...")

    runner = PaperTradingRunner(
        initial_balance=10_000.0,
        strategy_name=STRATEGY_NAME,
    )

    result = runner.run(
        DATA_FILE,
        strategy_transform=v5_transform,
    )

    assert isinstance(
        result,
        dict,
    ), "Paper runner did not return a dictionary."

    print(
        "PASS: V5 paper simulation completed"
    )

    # --------------------------------------------------------
    # 4. Validate runner result structure.
    # --------------------------------------------------------

    print()
    print("[4/5] Validating runner result...")

    expected_keys = {
        "status",
        "strategy_name",
        "market_data_file",
        "pipeline",
        "data",
        "paper_report",
        "paper_evaluation",
        "unified_health",
        "evaluation",
        "session_id",
        "session",
        "monitor",
        "record_counts",
    }

    missing_keys = (
        expected_keys
        - set(result.keys())
    )

    assert not missing_keys, (
        "Runner result is missing keys: "
        + ", ".join(sorted(missing_keys))
    )

    assert result["status"] == "COMPLETE", (
        f"Unexpected runner status: "
        f"{result['status']}"
    )

    assert (
        result["strategy_name"]
        == STRATEGY_NAME
    ), (
        "Unexpected strategy name: "
        f"{result['strategy_name']}"
    )

    assert result["session_id"], (
        "No paper session ID was returned."
    )

    assert isinstance(
        result["paper_report"],
        dict,
    ), "paper_report is not a dictionary."

    assert isinstance(
        result["paper_evaluation"],
        dict,
    ), "paper_evaluation is not a dictionary."

    assert isinstance(
        result["record_counts"],
        dict,
    ), "record_counts is not a dictionary."

    print(
        "PASS: runner returned the expected "
        "persistent paper-session structure"
    )

    # --------------------------------------------------------
    # 5. Validate V5 performance and persistence.
    # --------------------------------------------------------

    print()
    print("[5/5] Validating V5 results...")

    paper_report = result["paper_report"]

    performance = paper_report.get(
        "performance",
        {},
    )

    data_report = paper_report.get(
        "data",
        {},
    )

    risk_report = paper_report.get(
        "risk",
        {},
    )

    trades = int(
        performance.get(
            "trades",
            0,
        )
        or 0
    )

    wins = int(
        performance.get(
            "wins",
            0,
        )
        or 0
    )

    losses = int(
        performance.get(
            "losses",
            0,
        )
        or 0
    )

    total_pnl = float(
        performance.get(
            "total_pnl",
            0.0,
        )
        or 0.0
    )

    strategy_signal_count = int(
        data_report.get(
            "strategy_signal_count",
            0,
        )
        or 0
    )

    strategy_blocked_signals = int(
        data_report.get(
            "strategy_blocked_signals",
            0,
        )
        or 0
    )

    allowed_entries = int(
        risk_report.get(
            "allowed_entries",
            0,
        )
        or 0
    )

    risk_event_count = int(
        risk_report.get(
            "risk_event_count",
            0,
        )
        or 0
    )

    print()
    print("V5 PAPER RESULT")
    print("-" * 40)
    print(f"Trades                 {trades}")
    print(f"Wins                   {wins}")
    print(f"Losses                 {losses}")
    print(
        f"Win rate               "
        f"{performance.get('win_rate', 0.0):.2%}"
    )
    print(
        f"Profit factor          "
        f"{performance.get('profit_factor', 0.0):.4f}"
    )
    print(
        f"P&L                    "
        f"{total_pnl:+.2f}"
    )
    print(
        f"Strategy signals       "
        f"{strategy_signal_count}"
    )
    print(
        f"Strategy blocked       "
        f"{strategy_blocked_signals}"
    )
    print(
        f"Allowed entries        "
        f"{allowed_entries}"
    )
    print(
        f"Risk events            "
        f"{risk_event_count}"
    )
    print(
        f"Session ID             "
        f"{result['session_id']}"
    )

    # The runner should report the same number of blocked
    # candidate signals that we calculated independently.
    assert (
        strategy_blocked_signals
        == total_v5_blocks
    ), (
        "Runner-reported blocked signal count "
        "does not match the exact V5 transform."
    )

    # The strategy signal count should equal the transformed
    # LONG/SHORT signal count calculated independently.
    assert (
        strategy_signal_count
        == transformed_signal_count
    ), (
        "Runner strategy signal count does not "
        "match the transformed signal count."
    )

    # The paper engine should have produced actual trades.
    assert trades > 0, (
        "V5 paper simulation produced zero trades."
    )

    # Wins + losses should account for all trades.
    assert (
        wins + losses
        == trades
    ), (
        "Wins + losses does not equal total trades."
    )

    # Allowed entries should match the actual paper trades
    # when no risk blocks occur.
    assert (
        allowed_entries == trades
    ), (
        "Allowed entries does not match "
        "paper trades."
    )

    # A risk event should exist for each evaluated entry.
    assert (
        risk_event_count >= trades
    ), (
        "Risk-event count is unexpectedly "
        "lower than the number of trades."
    )

    # Persistence must contain the completed session.
    record_counts = result[
        "record_counts"
    ]

    sessions = int(
        record_counts.get(
            "sessions",
            0,
        )
        or 0
    )

    persisted_trades = int(
        record_counts.get(
            "trades",
            0,
        )
        or 0
    )

    assert sessions >= 1, (
        "No paper session was persisted."
    )

    assert persisted_trades == trades, (
        "Persisted trade count does not "
        "match the paper report."
    )

    print()
    print(
        "PASS: V5 performance and persistence "
        "checks passed"
    )

    print()
    print("=" * 80)
    print("PAPER TRADING V5 TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()