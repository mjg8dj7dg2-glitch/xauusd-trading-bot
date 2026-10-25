from engines.pipeline import TradingPipeline
from engines.pattern_validation import (
    PatternValidationAnalyzer,
    print_validation_report,
)


DATA_FILE = "data\\xauusd\\raw\\XAUUSD_5m.csv"


def main():
    print()
    print("=" * 70)
    print("REAL XAUUSD OUT-OF-SAMPLE PATTERN VALIDATION")
    print("=" * 70)

    print()
    print("Running the real XAUUSD backtest...")
    print(f"File: {DATA_FILE}")

    pipeline = TradingPipeline(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        commission_per_trade=0.0,
        slippage_per_trade=0.0,
        minimum_rows=100,
        correlation_window=20,
        maximum_absolute_correlation=0.80,
        news_before_minutes=30,
        news_after_minutes=15,
    )

    result = pipeline.run(DATA_FILE)

    backtest = result["backtest"]
    trades = backtest.get("trades", [])

    print()
    print("BACKTEST VALIDATION")
    print("-" * 70)

    print(
        f"Trades returned by backtest: "
        f"{len(trades)}"
    )

    if not trades:
        print("ERROR: No trades returned.")
        raise SystemExit(1)

    expected_trade_count = backtest.get(
        "total_trades",
        len(trades),
    )

    if len(trades) != expected_trade_count:
        print(
            "ERROR: Trade count mismatch."
        )
        print(
            f"Summary: {expected_trade_count}"
        )
        print(
            f"Trades : {len(trades)}"
        )
        raise SystemExit(1)

    print("Trade count consistency: PASSED")

    # ---------------------------------------------------------
    # CREATE VALIDATOR
    # ---------------------------------------------------------

    validator = PatternValidationAnalyzer(
        trades=trades,

        # First 70% is used only to discover patterns.
        discovery_fraction=0.70,

        # A pattern must have at least 5 trades
        # in the discovery period.
        minimum_discovery_trades=5,

        # A discovered pattern must appear at least
        # 3 times in the validation period before
        # we consider its validation result.
        minimum_validation_trades=3,
    )

    discovery_df, validation_df = (
        validator.split_data()
    )

    print()
    print("CHRONOLOGICAL SPLIT")
    print("-" * 70)

    print(
        f"Discovery trades : "
        f"{len(discovery_df)}"
    )

    print(
        f"Validation trades: "
        f"{len(validation_df)}"
    )

    if len(discovery_df) == 0:
        print(
            "ERROR: Discovery dataset is empty."
        )
        raise SystemExit(1)

    if len(validation_df) == 0:
        print(
            "ERROR: Validation dataset is empty."
        )
        raise SystemExit(1)

    total_split = (
        len(discovery_df)
        + len(validation_df)
    )

    if total_split != len(trades):
        print(
            "ERROR: Chronological split does not "
            "contain all trades."
        )
        raise SystemExit(1)

    print(
        "Chronological split consistency: PASSED"
    )

    # ---------------------------------------------------------
    # BUILD VALIDATION REPORT
    # ---------------------------------------------------------

    report = validator.build_report()

    print_validation_report(
        report,
        limit=30,
    )

    # ---------------------------------------------------------
    # VALIDATION CHECKS
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("OUT-OF-SAMPLE VALIDATION CHECKS")
    print("=" * 70)

    required_keys = [
        "discovery_trades",
        "validation_trades",
        "validated_patterns",
    ]

    missing_keys = [
        key
        for key in required_keys
        if key not in report
    ]

    if missing_keys:
        print(
            "ERROR: Missing report keys:"
        )

        for key in missing_keys:
            print(
                f" - {key}"
            )

        raise SystemExit(1)

    print(
        "Report structure: PASSED"
    )

    if (
        report["discovery_trades"]
        != len(discovery_df)
    ):
        print(
            "ERROR: Discovery trade count mismatch."
        )
        raise SystemExit(1)

    print(
        "Discovery count: PASSED"
    )

    if (
        report["validation_trades"]
        != len(validation_df)
    ):
        print(
            "ERROR: Validation trade count mismatch."
        )
        raise SystemExit(1)

    print(
        "Validation count: PASSED"
    )

    patterns = report[
        "validated_patterns"
    ]

    for pattern in patterns:
        if "conditions" not in pattern:
            print(
                "ERROR: Pattern is missing conditions."
            )
            raise SystemExit(1)

        if "discovery" not in pattern:
            print(
                "ERROR: Pattern is missing "
                "discovery metrics."
            )
            raise SystemExit(1)

        if "validation" not in pattern:
            print(
                "ERROR: Pattern is missing "
                "validation metrics."
            )
            raise SystemExit(1)

        if "stability" not in pattern:
            print(
                "ERROR: Pattern is missing "
                "stability classification."
            )
            raise SystemExit(1)

    print(
        "Pattern structure: PASSED"
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    positive_stable = sum(
        1
        for pattern in patterns
        if pattern["stability"]
        == "POSITIVE_STABLE"
    )

    negative_stable = sum(
        1
        for pattern in patterns
        if pattern["stability"]
        == "NEGATIVE_STABLE"
    )

    reversed_patterns = sum(
        1
        for pattern in patterns
        if pattern["stability"]
        in [
            "REVERSED_TO_NEGATIVE",
            "REVERSED_TO_POSITIVE",
        ]
    )

    mixed_patterns = sum(
        1
        for pattern in patterns
        if pattern["stability"]
        == "MIXED"
    )

    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    print(
        f"Patterns validated        : "
        f"{len(patterns)}"
    )

    print(
        f"Positive stable patterns  : "
        f"{positive_stable}"
    )

    print(
        f"Negative stable patterns  : "
        f"{negative_stable}"
    )

    print(
        f"Reversed patterns         : "
        f"{reversed_patterns}"
    )

    print(
        f"Mixed patterns            : "
        f"{mixed_patterns}"
    )

    print()
    print("=" * 70)
    print(
        "REAL XAUUSD OUT-OF-SAMPLE "
        "PATTERN VALIDATION TEST PASSED"
    )
    print("=" * 70)

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "No strategy parameters were changed."
    )
    print(
        "No trading rules were added or removed."
    )
    print(
        "This test only checks whether discovered "
        "patterns persisted in later trades."
    )


if __name__ == "__main__":
    main()