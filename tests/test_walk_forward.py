"""
Test the walk-forward validation engine on the real XAUUSD dataset.
"""

from __future__ import annotations

import pandas as pd

from engines.market_data import load_csv
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.technical import add_technical_features
from engines.walk_forward import (
    WalkForwardEngine,
    format_walk_forward_report,
)


DATA_PATH = "data/xauusd/raw/XAUUSD_5m.csv"


def build_analyzed_data() -> pd.DataFrame:
    data = load_csv(DATA_PATH)

    technical = add_technical_features(data)
    regime = add_market_regime(technical)
    signals = generate_signals(regime)

    return signals


def main():
    print(
        "WALK-FORWARD VALIDATION TEST"
    )
    print("=" * 120)

    print()
    print("1. Loading real XAUUSD data...")
    analyzed_data = build_analyzed_data()
    print(
        f"Rows loaded: {len(analyzed_data)}"
    )

    print()
    print("2. Creating walk-forward engine...")

    engine = WalkForwardEngine(
        development_days=70,
        validation_days=28,
        step_days=28,
        minimum_validation_trades=5,
    )

    print(
        "Engine ready."
    )

    print()
    print("3. Building chronological windows...")

    windows = engine.build_windows(
        analyzed_data
    )

    print(
        f"Windows created: {len(windows)}"
    )

    assert len(windows) >= 3, (
        "Expected at least 3 walk-forward windows."
    )

    for window in windows:
        assert (
            window.development_end
            <= window.validation_start
        )

        assert (
            window.development_start
            < window.development_end
        )

        assert (
            window.validation_start
            < window.validation_end
        )

    print(
        "Window chronology checks passed."
    )

    print()
    print("4. Running walk-forward validation...")
    print("=" * 120)

    report = engine.run(
        analyzed_data
    )

    print(
        format_walk_forward_report(
            report
        )
    )

    print()
    print(
        "5. Integrity checks..."
    )
    print("=" * 120)

    aggregate = report["aggregate"]

    expected_variants = {
        "V1_BASELINE",
        "V2_BLOCK_SHORT_ATR_8_12",
        "V3_BLOCK_LOW_VOL_THURSDAY",
        "V4_BLOCK_SHORT_LOW_VOL",
        "V5_V2_PLUS_V3",
        "V6_V2_PLUS_V4",
    }

    assert set(aggregate) == expected_variants, (
        "The six expected variants were not all evaluated."
    )

    for variant_name in expected_variants:
        summary = aggregate[variant_name]

        assert (
            summary["windows_total"]
            == len(report["windows"])
        )

        assert (
            summary["validation"]["trades"]
            >= 0
        )

        assert (
            0.0
            <= summary["validation"]["win_rate"]
            <= 1.0
        )

        assert (
            0.0
            <= summary["validation"]["max_drawdown"]
        )

        assert (
            0.0
            <= summary["pf_consistency"]
            <= 1.0
        )

        assert (
            0.0
            <= summary["pnl_consistency"]
            <= 1.0
        )

    print(
        "All six variants evaluated."
    )

    print(
        "Chronological windows verified."
    )

    print(
        "Consistency metrics verified."
    )

    print()
    print(
        "WALK-FORWARD VALIDATION TEST PASSED"
    )


if __name__ == "__main__":
    main()
