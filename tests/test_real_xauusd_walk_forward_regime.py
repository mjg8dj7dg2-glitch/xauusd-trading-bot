from pathlib import Path

import pandas as pd

from engines.strategy import generate_signals
from engines.walk_forward import WalkForwardEngine
from engines.regime_robustness import RegimeRobustnessAnalyzer


DATA_PATH = Path("data/xauusd/raw/XAUUSD_5m.csv")


def load_xauusd():
    """Load and normalize the existing XAUUSD CSV."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"XAUUSD data file was not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = {
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            "XAUUSD CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )

    # The actual CSV uses "datetime".
    # The engines expect "timestamp".
    df = df.rename(
        columns={
            "datetime": "timestamp"
        }
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
        errors="coerce",
    )

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        ]
    )

    df = df.sort_values(
        "timestamp"
    )

    df = df.drop_duplicates(
        subset=["timestamp"],
        keep="last",
    )

    df = df.reset_index(
        drop=True
    )

    return df


def prepare_data(df):
    """Create the technical, regime and signal columns."""

    from engines.technical import add_technical_features
    from engines.regime import add_market_regime

    result = df.copy()

    result = add_technical_features(
        result
    )

    result = add_market_regime(
        result
    )

    result = generate_signals(
        result
    )

    return result


def profit_factor(trades):
    """Calculate profit factor."""

    gross_profit = sum(
        float(trade.get("pnl", 0.0))
        for trade in trades
        if float(trade.get("pnl", 0.0)) > 0
    )

    gross_loss = sum(
        abs(float(trade.get("pnl", 0.0)))
        for trade in trades
        if float(trade.get("pnl", 0.0)) < 0
    )

    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")

        return 0.0

    return gross_profit / gross_loss


def max_drawdown(trades):
    """Calculate chronological trade-equity drawdown."""

    balance = 10000.0
    peak = balance
    largest = 0.0

    ordered = sorted(
        trades,
        key=lambda trade: pd.to_datetime(
            trade.get("entry_time"),
            utc=True,
            errors="coerce",
        )
        if trade.get("entry_time") is not None
        else pd.Timestamp.min.tz_localize("UTC"),
    )

    for trade in ordered:
        balance += float(
            trade.get("pnl", 0.0)
        )

        peak = max(
            peak,
            balance,
        )

        if peak > 0:
            drawdown = (
                peak - balance
            ) / peak

            largest = max(
                largest,
                drawdown,
            )

    return largest


def summarize_trades(trades):
    """Create a compact trade summary."""

    total = len(trades)

    if total == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "pnl": 0.0,
            "drawdown": 0.0,
        }

    wins = sum(
        1
        for trade in trades
        if (
            str(
                trade.get(
                    "result",
                    "",
                )
            ).upper()
            == "WIN"
            or float(
                trade.get(
                    "pnl",
                    0.0,
                )
            )
            > 0
        )
    )

    losses = sum(
        1
        for trade in trades
        if float(
            trade.get(
                "pnl",
                0.0,
            )
        )
        < 0
    )

    total_pnl = sum(
        float(
            trade.get(
                "pnl",
                0.0,
            )
        )
        for trade in trades
    )

    return {
        "trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total,
        "profit_factor": profit_factor(
            trades
        ),
        "pnl": total_pnl,
        "drawdown": max_drawdown(
            trades
        ),
    }


def print_trade_summary(summary):
    print(
        f"Trades           : {summary['trades']}"
    )

    print(
        f"Wins             : {summary['wins']}"
    )

    print(
        f"Losses           : {summary['losses']}"
    )

    print(
        f"Win rate         : {summary['win_rate']:.2%}"
    )

    pf = summary["profit_factor"]

    if pf == float("inf"):
        print(
            "Profit factor    : INF"
        )
    else:
        print(
            f"Profit factor    : {pf:.4f}"
        )

    print(
        f"P&L              : {summary['pnl']:.2f}"
    )

    print(
        f"Max drawdown     : {summary['drawdown']:.2%}"
    )


def print_regime_table(
    analyzer,
    trades,
    title,
):
    """Print regime robustness results."""

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    if not trades:
        print(
            "No trades available for this analysis."
        )
        return

    report = analyzer.analyze_all(
        trades
    )

    for category, rows in report.items():

        print()
        print(
            category.upper()
        )
        print("-" * 80)

        if not isinstance(
            rows,
            list,
        ):
            print(
                rows
            )
            continue

        if not rows:
            print(
                "No groups with enough data."
            )
            continue

        for row in rows:

            if not isinstance(
                row,
                dict,
            ):
                print(
                    row
                )
                continue

            group = row.get(
                "group",
                row.get(
                    "name",
                    "UNKNOWN",
                ),
            )

            trade_count = row.get(
                "trades",
                0,
            )

            win_rate = row.get(
                "win_rate",
                0.0,
            )

            pf = row.get(
                "profit_factor",
                0.0,
            )

            pnl = row.get(
                "total_pnl",
                row.get(
                    "pnl",
                    0.0,
                ),
            )

            status = row.get(
                "status",
                "",
            )

            if pf == float("inf"):
                pf_text = "INF"
            else:
                pf_text = (
                    f"{float(pf):.4f}"
                )

            print(
                f"{str(group):35} "
                f"trades={int(trade_count):4} "
                f"win={float(win_rate):.2%} "
                f"PF={pf_text:>8} "
                f"P&L={float(pnl):>10.2f}"
                + (
                    f"  {status}"
                    if status
                    else ""
                )
            )


def main():

    print()
    print(
        "XAUUSD WALK-FORWARD × REGIME ANALYSIS"
    )
    print("=" * 80)

    # ------------------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------------------

    print()
    print(
        "Loading XAUUSD data..."
    )

    df = load_xauusd()

    print(
        f"Rows       : {len(df)}"
    )

    print(
        f"Start      : {df['timestamp'].min()}"
    )

    print(
        f"End        : {df['timestamp'].max()}"
    )

    print(
        f"Columns    : {list(df.columns)}"
    )

    # ------------------------------------------------------------------
    # PREPARE DATA
    # ------------------------------------------------------------------

    print()
    print(
        "Preparing technical indicators, regimes and signals..."
    )

    analyzed_data = prepare_data(
        df
    )

    print(
        f"Prepared rows: {len(analyzed_data)}"
    )

    # ------------------------------------------------------------------
    # WALK-FORWARD ENGINE
    # ------------------------------------------------------------------

    engine = WalkForwardEngine(
        development_days=70,
        validation_days=28,
        step_days=28,
        minimum_validation_trades=5,
    )

    # Use the same standard variants already defined
    # by the StrategyExperiment.
    variants = engine.experiment.get_standard_variants()

    print()
    print(
        "Strategy variants:"
    )

    for name, _ in variants:
        print(
            f"  - {name}"
        )

    # ------------------------------------------------------------------
    # RUN WALK-FORWARD
    # ------------------------------------------------------------------

    print()
    print(
        "Running chronological walk-forward analysis..."
    )

    results = engine.run(
        analyzed_data=analyzed_data,
        variants=variants,
    )

    print()
    print(
        "Walk-forward analysis completed."
    )

    # ------------------------------------------------------------------
    # AGGREGATE RESULTS
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print(
        "WALK-FORWARD AGGREGATE RESULTS"
    )
    print("=" * 80)

    aggregate = results[
        "aggregate"
    ]

    for variant_name, summary in aggregate.items():

        validation = summary[
            "validation"
        ]

        print()
        print(
            variant_name
        )
        print("-" * 80)

        print(
            f"Validation trades : "
            f"{validation['trades']}"
        )

        print(
            f"Validation win    : "
            f"{validation['win_rate']:.2%}"
        )

        pf = validation[
            "profit_factor"
        ]

        if pf is None:
            print(
                "Validation PF     : INF"
            )
        else:
            print(
                f"Validation PF     : "
                f"{float(pf):.4f}"
            )

        print(
            f"Validation P&L    : "
            f"{validation['total_pnl']:.2f}"
        )

        print(
            f"Validation DD     : "
            f"{validation['max_drawdown']:.2%}"
        )

        print(
            f"Windows total     : "
            f"{summary['windows_total']}"
        )

        print(
            f"Windows enough    : "
            f"{summary['windows_with_enough_trades']}"
        )

        print(
            f"PF > 1 windows    : "
            f"{summary['windows_pf_above_1']}"
        )

        print(
            f"Positive P&L wins  : "
            f"{summary['windows_pnl_positive']}"
        )

        print(
            f"PF consistency     : "
            f"{summary['pf_consistency']:.2%}"
        )

        print(
            f"P&L consistency    : "
            f"{summary['pnl_consistency']:.2%}"
        )

        if (
            variant_name != "V1_BASELINE"
            and "vs_baseline" in summary
        ):
            comparison = summary[
                "vs_baseline"
            ]

            print()
            print(
                "Vs baseline:"
            )

            print(
                f"  Trade change     : "
                f"{comparison['validation_trade_change']:+d}"
            )

            print(
                f"  Win-rate change  : "
                f"{comparison['validation_win_rate_change']:+.2%}"
            )

            pf_change = comparison[
                "validation_profit_factor_change"
            ]

            if pf_change is None:
                print(
                    "  PF change        : N/A"
                )
            else:
                print(
                    f"  PF change        : "
                    f"{pf_change:+.4f}"
                )

            print(
                f"  P&L change       : "
                f"{comparison['validation_pnl_change']:+.2f}"
            )

            print(
                f"  DD change        : "
                f"{comparison['validation_drawdown_change']:+.2%}"
            )

    # ------------------------------------------------------------------
    # WINDOW-BY-WINDOW RESULTS
    # ------------------------------------------------------------------

    windows = results[
        "windows"
    ]

    print()
    print("=" * 80)
    print(
        "WINDOW-BY-WINDOW RESULTS"
    )
    print("=" * 80)

    for report in windows:

        window = report[
            "window"
        ]

        print()
        print(
            f"WINDOW {window.index}"
        )
        print("-" * 80)

        print(
            f"Development : "
            f"{window.development_start} "
            f"-> "
            f"{window.development_end}"
        )

        print(
            f"Validation  : "
            f"{window.validation_start} "
            f"-> "
            f"{window.validation_end}"
        )

        print(
            f"Development rows: "
            f"{report['development_rows']}"
        )

        print(
            f"Validation rows : "
            f"{report['validation_rows']}"
        )

        for variant_name, variant_report in report[
            "variants"
        ].items():

            validation = variant_report[
                "validation"
            ]

            print()
            print(
                f"{variant_name}:"
            )

            print(
                f"  Trades       : "
                f"{validation['trades']}"
            )

            print(
                f"  Win rate     : "
                f"{validation['win_rate']:.2%}"
            )

            pf = validation[
                "profit_factor"
            ]

            if pf is None:
                print(
                    "  Profit factor: INF"
                )
            else:
                print(
                    f"  Profit factor: "
                    f"{float(pf):.4f}"
                )

            print(
                f"  P&L         : "
                f"{validation['total_pnl']:.2f}"
            )

            print(
                f"  Drawdown    : "
                f"{validation['max_drawdown']:.2%}"
            )

    # ------------------------------------------------------------------
    # REGIME ANALYSIS PER WALK-FORWARD WINDOW
    # ------------------------------------------------------------------

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=5
    )

    print()
    print("=" * 80)
    print(
        "WALK-FORWARD × REGIME ANALYSIS"
    )
    print("=" * 80)

    for report in windows:

        window = report[
            "window"
        ]

        print()
        print(
            f"WINDOW {window.index}"
        )
        print(
            f"Validation: "
            f"{window.validation_start} "
            f"-> "
            f"{window.validation_end}"
        )

        for variant_name, variant_report in report[
            "variants"
        ].items():

            validation_result = variant_report[
                "validation_result"
            ]

            trades = validation_result.get(
                "trades",
                [],
            )

            print()
            print(
                f"VARIANT: {variant_name}"
            )

            summary = summarize_trades(
                trades
            )

            print_trade_summary(
                summary
            )

            if not trades:
                print(
                    "No trades to analyze by regime."
                )
                continue

            print_regime_table(
                analyzer,
                trades,
                (
                    f"WINDOW {window.index} "
                    f"- {variant_name} "
                    f"- REGIME DETAILS"
                ),
            )

    # ------------------------------------------------------------------
    # COMBINED VALIDATION REGIME ANALYSIS
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print(
        "COMBINED WALK-FORWARD REGIME ANALYSIS"
    )
    print("=" * 80)

    for variant_name, _ in variants:

        combined_trades = []

        for report in windows:

            validation_result = report[
                "variants"
            ][variant_name][
                "validation_result"
            ]

            combined_trades.extend(
                validation_result.get(
                    "trades",
                    [],
                )
            )

        print()
        print(
            f"VARIANT: {variant_name}"
        )

        summary = summarize_trades(
            combined_trades
        )

        print_trade_summary(
            summary
        )

        if not combined_trades:
            continue

        print_regime_table(
            analyzer,
            combined_trades,
            (
                f"COMBINED REGIME "
                f"DETAILS - {variant_name}"
            ),
        )

        # --------------------------------------------------------------
        # WEAK REGIMES
        # --------------------------------------------------------------

        weak = analyzer.find_weak_regimes(
            combined_trades
        )

        print()
        print(
            "WEAK REGIME CATEGORIES"
        )
        print("-" * 80)

        if weak:
            for category, rows in weak.items():

                print()
                print(
                    category
                )

                if isinstance(
                    rows,
                    list,
                ):
                    for row in rows:
                        print(
                            f"  {row}"
                        )
        else:
            print(
                "No weak regime categories found."
            )

        # --------------------------------------------------------------
        # POSITIVE REGIMES
        # --------------------------------------------------------------

        positive = analyzer.find_positive_regimes(
            combined_trades
        )

        print()
        print(
            "POSITIVE REGIME CATEGORIES"
        )
        print("-" * 80)

        if positive:
            for category, rows in positive.items():

                print()
                print(
                    category
                )

                if isinstance(
                    rows,
                    list,
                ):
                    for row in rows:
                        print(
                            f"  {row}"
                        )
        else:
            print(
                "No positive regime categories found."
            )

    # ------------------------------------------------------------------
    # COMPLETE
    # ------------------------------------------------------------------

    print()
    print("=" * 80)
    print(
        "WALK-FORWARD × REGIME ANALYSIS COMPLETE"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()