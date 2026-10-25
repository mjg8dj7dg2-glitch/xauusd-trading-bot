from engines.pipeline import TradingPipeline
from engines.trade_analysis import TradeAnalyzer


DATA_FILE = "data\\xauusd\\raw\\XAUUSD_5m.csv"


def print_performance_table(title, data):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    if not data:
        print("No data available.")
        return

    for name, result in data.items():
        print()
        print(name)
        print("-" * 50)

        print(f"Trades        : {result.get('trades', 0)}")
        print(f"Wins          : {result.get('wins', 0)}")
        print(f"Losses        : {result.get('losses', 0)}")
        print(
            f"Win rate      : "
            f"{result.get('win_rate', 0.0):.4f}"
        )

        profit_factor = result.get(
            "profit_factor",
            0.0,
        )

        if profit_factor == float("inf"):
            profit_factor_text = "INF"
        else:
            profit_factor_text = f"{profit_factor:.4f}"

        print(
            f"Profit factor : "
            f"{profit_factor_text}"
        )

        print(
            f"Total P&L     : "
            f"{result.get('total_pnl', 0.0):.2f}"
        )

        print(
            f"Average P&L   : "
            f"{result.get('average_pnl', 0.0):.2f}"
        )


def main():
    print()
    print("=" * 70)
    print("DEEP REAL XAUUSD TRADE ANALYSIS")
    print("=" * 70)

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

    trades = result["backtest"].get("trades", [])

    print()
    print(f"Completed trades: {len(trades)}")

    if not trades:
        print("ERROR: No trades available.")
        raise SystemExit(1)

    analyzer = TradeAnalyzer(trades)
    report = analyzer.build_report()

    # ---------------------------------------------------------
    # TIME OF DAY
    # ---------------------------------------------------------

    print_performance_table(
        "PERFORMANCE BY UTC ENTRY HOUR",
        report["time_of_day"],
    )

    # ---------------------------------------------------------
    # WEEKDAY
    # ---------------------------------------------------------

    print_performance_table(
        "PERFORMANCE BY WEEKDAY",
        report["weekdays"],
    )

    # ---------------------------------------------------------
    # EXCURSION ANALYSIS
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("MAE / MFE ANALYSIS")
    print("=" * 70)

    excursions = report["excursions"]

    if not excursions:
        print("No MAE/MFE data available.")

    for name, values in excursions.items():
        print()
        print(name.upper())
        print("-" * 50)

        print(f"Count    : {values['count']}")
        print(
            f"Average  : "
            f"{values['average']}"
        )
        print(
            f"Median   : "
            f"{values['median']}"
        )
        print(
            f"Maximum  : "
            f"{values['maximum']}"
        )

    # ---------------------------------------------------------
    # RESULT + DIRECTION COMBINATION
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("DIRECTION + RESULT BREAKDOWN")
    print("=" * 70)

    trade_df = analyzer.df

    if (
        not trade_df.empty
        and "direction" in trade_df.columns
        and "result" in trade_df.columns
    ):
        combination = (
            trade_df
            .groupby(
                ["direction", "result"],
                dropna=False,
            )
            .size()
            .reset_index(name="trades")
        )

        print(combination.to_string(index=False))

    # ---------------------------------------------------------
    # DIRECTION + EXIT REASON
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("DIRECTION + EXIT REASON")
    print("=" * 70)

    if (
        not trade_df.empty
        and "direction" in trade_df.columns
        and "exit_reason" in trade_df.columns
    ):
        combination = (
            trade_df
            .groupby(
                ["direction", "exit_reason"],
                dropna=False,
            )
            .agg(
                trades=("pnl", "count"),
                total_pnl=("pnl", "sum"),
                average_pnl=("pnl", "mean"),
            )
            .reset_index()
        )

        print(
            combination.to_string(
                index=False
            )
        )

    # ---------------------------------------------------------
    # WINNERS VS LOSERS
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("WINNERS VS LOSERS")
    print("=" * 70)

    if not trade_df.empty:
        winners = trade_df[
            trade_df["result"] == "WIN"
        ]

        losers = trade_df[
            trade_df["result"] == "LOSS"
        ]

        indicator_columns = [
            "rsi",
            "atr",
            "ema",
            "sma",
            "entry_price",
            "signal_strength",
        ]

        for column in indicator_columns:
            if column not in trade_df.columns:
                continue

            winner_values = (
                winners[column]
                .dropna()
            )

            loser_values = (
                losers[column]
                .dropna()
            )

            print()
            print(column)

            if len(winner_values):
                print(
                    f"  Winner average: "
                    f"{winner_values.mean():.6f}"
                )
                print(
                    f"  Winner median : "
                    f"{winner_values.median():.6f}"
                )

            if len(loser_values):
                print(
                    f"  Loser average : "
                    f"{loser_values.mean():.6f}"
                )
                print(
                    f"  Loser median  : "
                    f"{loser_values.median():.6f}"
                )

    # ---------------------------------------------------------
    # RECENT ROLLING PERFORMANCE
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("LAST 10 ROLLING 20-TRADE WINDOWS")
    print("=" * 70)

    rolling = report["rolling_performance"]

    if not rolling:
        print("Not enough trades for rolling analysis.")
    else:
        for row in rolling[-10:]:
            pf = row["profit_factor"]

            if pf == float("inf"):
                pf_text = "INF"
            else:
                pf_text = f"{pf:.4f}"

            print(
                f"Trade #{row['trade_number']:3d} | "
                f"Win rate={row['win_rate']:.4f} | "
                f"PF={pf_text} | "
                f"P&L={row['total_pnl']:.2f}"
            )

    # ---------------------------------------------------------
    # FINAL VALIDATION
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("DEEP ANALYSIS VALIDATION")
    print("=" * 70)

    required_sections = [
        "time_of_day",
        "weekdays",
        "excursions",
        "rolling_performance",
    ]

    for section in required_sections:
        if section not in report:
            print(
                f"ERROR: Missing section: {section}"
            )
            raise SystemExit(1)

    print("Required deep-analysis sections: PASSED")

    print()
    print("=" * 70)
    print("DEEP XAUUSD ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()