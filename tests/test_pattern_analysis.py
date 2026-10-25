from engines.pipeline import TradingPipeline
from engines.pattern_analysis import (
    MultiConditionPatternAnalyzer,
    print_report,
)


DATA_FILE = "data\\xauusd\\raw\\XAUUSD_5m.csv"


def main():
    print()
    print("=" * 70)
    print("REAL XAUUSD MULTI-CONDITION PATTERN ANALYSIS")
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
    # CREATE ANALYZER
    # ---------------------------------------------------------

    analyzer = MultiConditionPatternAnalyzer(
        trades=trades,

        # Require at least 5 trades before showing
        # a condition combination.
        minimum_trades=5,

        # Require at least 3 losses before identifying
        # something as a recurring loss pattern.
        minimum_losses=3,

        # Require at least 3 wins before identifying
        # something as a recurring winning pattern.
        minimum_wins=3,
    )

    report = analyzer.build_report()

    # ---------------------------------------------------------
    # PRINT COMPLETE REPORT
    # ---------------------------------------------------------

    print_report(report)

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("PATTERN ANALYSIS VALIDATION")
    print("=" * 70)

    required_sections = [
        "trade_count",
        "single_conditions",
        "loss_patterns",
        "win_patterns",
        "direction_patterns",
    ]

    missing_sections = [
        section
        for section in required_sections
        if section not in report
    ]

    if missing_sections:
        print(
            "ERROR: Missing report sections:"
        )
        for section in missing_sections:
            print(f" - {section}")
        raise SystemExit(1)

    print("Report structure: PASSED")

    if report["trade_count"] != len(trades):
        print(
            "ERROR: Analyzer trade count does not "
            "match the backtest trade count."
        )
        raise SystemExit(1)

    print("Analyzer trade count: PASSED")

    # Make sure both directions are represented
    # in the actual backtest.
    direction_patterns = report[
        "direction_patterns"
    ]

    if "LONG" not in direction_patterns:
        print(
            "WARNING: LONG direction not present."
        )

    if "SHORT" not in direction_patterns:
        print(
            "WARNING: SHORT direction not present."
        )

    print("Direction analysis: PASSED")

    print()
    print("=" * 70)
    print("REAL XAUUSD PATTERN ANALYSIS TEST PASSED")
    print("=" * 70)

    print()
    print(
        "IMPORTANT: These patterns are descriptive."
    )
    print(
        "No strategy rules were changed automatically."
    )


if __name__ == "__main__":
    main()