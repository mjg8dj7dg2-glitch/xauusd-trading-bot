from engines.pipeline import TradingPipeline
from engines.trade_analysis import TradeAnalyzer, print_report


DATA_FILE = "data\\xauusd\\raw\\XAUUSD_5m.csv"


def main():
    print()
    print("=" * 70)
    print("REAL XAUUSD TRADE ANALYSIS")
    print("=" * 70)

    print()
    print("Loading and analyzing real XAUUSD data...")
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
    print("BACKTEST TRADE COUNT")
    print("-" * 70)
    print(f"Trades returned by backtest: {len(trades)}")

    if not trades:
        print()
        print("ERROR: No completed trades were returned.")
        raise SystemExit(1)

    analyzer = TradeAnalyzer(trades)
    report = analyzer.build_report()

    print_report(report)

    print()
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    expected_trade_count = backtest.get(
        "total_trades",
        len(trades),
    )

    if len(trades) != expected_trade_count:
        print(
            "WARNING: Trade count mismatch between "
            "backtest summary and trade list."
        )
        print(f"Summary count: {expected_trade_count}")
        print(f"Trade list:    {len(trades)}")
    else:
        print("Trade count consistency: PASSED")

    overall = report["overall"]

    if overall["trades"] != len(trades):
        print("ERROR: Analyzer trade count is incorrect.")
        raise SystemExit(1)

    print("Analyzer trade count: PASSED")

    required_sections = [
        "directions",
        "trend_regimes",
        "volatility_regimes",
        "exit_reasons",
        "results",
        "time_of_day",
        "weekdays",
        "indicators",
        "excursions",
        "losing_streaks",
        "losing_patterns",
        "rolling_performance",
        "period_comparison",
    ]

    missing_sections = [
        section
        for section in required_sections
        if section not in report
    ]

    if missing_sections:
        print(
            "ERROR: Missing analysis sections:",
            missing_sections,
        )
        raise SystemExit(1)

    print("Analysis sections: PASSED")

    print()
    print("=" * 70)
    print("REAL XAUUSD TRADE ANALYSIS TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()