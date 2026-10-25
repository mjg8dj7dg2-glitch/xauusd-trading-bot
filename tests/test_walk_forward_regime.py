from pathlib import Path

import pandas as pd

from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.technical import add_technical_features
from engines.walk_forward import WalkForwardEngine


DATA_PATH = Path("data/xauusd/raw/XAUUSD_5m.csv")

VARIANTS = [
    "V1_BASELINE",
    "V2_BLOCK_SHORT_ATR_8_12",
    "V3_BLOCK_LOW_VOL_THURSDAY",
    "V4_BLOCK_SHORT_LOW_VOL",
    "V5_V2_PLUS_V3",
    "V6_V2_PLUS_V4",
]


TARGET_GROUPS = [
    ("SHORT", ["direction"], ["SHORT"]),
    ("TRENDING_DOWN", ["trend_regime"], ["TRENDING_DOWN"]),
    (
        "SHORT + TRENDING_DOWN",
        ["direction", "trend_regime"],
        ["SHORT", "TRENDING_DOWN"],
    ),
    (
        "TRENDING_DOWN + LOW_VOLATILITY",
        ["trend_regime", "volatility_regime"],
        ["TRENDING_DOWN", "LOW_VOLATILITY"],
    ),
    (
        "SHORT + LOW_VOLATILITY",
        ["direction", "volatility_regime"],
        ["SHORT", "LOW_VOLATILITY"],
    ),
    (
        "SHORT + TRENDING_DOWN + LOW_VOLATILITY",
        ["direction", "trend_regime", "volatility_regime"],
        ["SHORT", "TRENDING_DOWN", "LOW_VOLATILITY"],
    ),
]


def load_real_data():
    print("1. Loading real XAUUSD data...")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"XAUUSD data file was not found: {DATA_PATH}"
        )

    # Use the raw XAUUSD file directly.
    # This diagnostic test should not depend on CSVDataSource's
    # instrument/timeframe mapping.
    df = pd.read_csv(DATA_PATH)

    required_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Raw XAUUSD CSV is missing required columns: "
            + ", ".join(missing)
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(
        drop=True
    )

    if df.empty:
        raise ValueError(
            "Raw XAUUSD CSV contains no rows."
        )

    print(f"Rows loaded: {len(df)}")
    print(
        f"Start: {df['timestamp'].iloc[0]}"
    )
    print(
        f"End:   {df['timestamp'].iloc[-1]}"
    )

    return df


def prepare_data(df):
    print(
        "\n2. Preparing technical indicators, "
        "regimes, and signals..."
    )

    result = add_technical_features(df)
    result = add_market_regime(result)
    result = generate_signals(result)

    print(
        f"Prepared rows: {len(result)}"
    )

    return result


def create_engine():
    print(
        "\n3. Creating walk-forward engine..."
    )

    engine = WalkForwardEngine(
        development_days=70,
        validation_days=28,
        step_days=28,
        minimum_validation_trades=5,
    )

    print("Engine ready.")

    return engine


def get_window_value(
    window,
    key,
    default=None,
):
    if isinstance(window, dict):
        return window.get(
            key,
            default,
        )

    return getattr(
        window,
        key,
        default,
    )


def get_validation_results(window):
    possible_keys = [
        "validation_results",
        "validation",
        "validation_trades",
    ]

    for key in possible_keys:
        value = get_window_value(
            window,
            key,
        )

        if value is not None:
            return value

    return None


def normalize_trades(results):
    if results is None:
        return []

    if isinstance(results, list):
        return results

    if isinstance(results, tuple):
        return list(results)

    if isinstance(results, pd.DataFrame):
        return results.to_dict(
            "records"
        )

    if isinstance(results, dict):
        if "trades" in results:
            trades = results["trades"]

            if isinstance(
                trades,
                pd.DataFrame,
            ):
                return trades.to_dict(
                    "records"
                )

            if isinstance(
                trades,
                list,
            ):
                return trades

        return []

    return []


def trade_matches_group(
    trade,
    columns,
    values,
):
    for column, expected in zip(
        columns,
        values,
    ):
        if trade.get(column) != expected:
            return False

    return True


def summarize_trades(trades):
    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
        }

    pnl_values = []

    for trade in trades:
        try:
            pnl = float(
                trade.get(
                    "pnl",
                    0.0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            pnl = 0.0

        pnl_values.append(
            pnl
        )

    wins = [
        pnl
        for pnl in pnl_values
        if pnl > 0
    ]

    losses = [
        pnl
        for pnl in pnl_values
        if pnl < 0
    ]

    gross_profit = sum(wins)
    gross_loss = abs(
        sum(losses)
    )

    if gross_loss == 0:
        if gross_profit > 0:
            profit_factor = float(
                "inf"
            )
        else:
            profit_factor = 0.0
    else:
        profit_factor = (
            gross_profit
            / gross_loss
        )

    return {
        "trades": len(
            pnl_values
        ),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (
            len(wins)
            / len(pnl_values)
        ),
        "profit_factor": profit_factor,
        "total_pnl": sum(
            pnl_values
        ),
    }


def extract_window_dates(
    window
):
    return (
        get_window_value(
            window,
            "development_start",
        ),
        get_window_value(
            window,
            "development_end",
        ),
        get_window_value(
            window,
            "validation_start",
        ),
        get_window_value(
            window,
            "validation_end",
        ),
    )


def run_integrity_checks(
    report
):
    print(
        "\n4. Checking report integrity..."
    )

    assert isinstance(
        report,
        dict,
    ), (
        "Walk-forward report "
        "must be a dictionary."
    )

    assert "windows" in report, (
        "Walk-forward report "
        "must contain 'windows'."
    )

    windows = report[
        "windows"
    ]

    assert isinstance(
        windows,
        list,
    ), (
        "Walk-forward report "
        "'windows' must be a list."
    )

    assert windows, (
        "Walk-forward report "
        "must contain at least "
        "one window."
    )

    previous_validation_end = None

    for index, window in enumerate(
        windows,
        start=1,
    ):
        (
            development_start,
            development_end,
            validation_start,
            validation_end,
        ) = extract_window_dates(
            window
        )

        assert (
            development_start
            is not None
        ), (
            f"Window {index} "
            "is missing "
            "development_start."
        )

        assert (
            development_end
            is not None
        ), (
            f"Window {index} "
            "is missing "
            "development_end."
        )

        assert (
            validation_start
            is not None
        ), (
            f"Window {index} "
            "is missing "
            "validation_start."
        )

        assert (
            validation_end
            is not None
        ), (
            f"Window {index} "
            "is missing "
            "validation_end."
        )

        assert (
            development_start
            < development_end
        ), (
            f"Window {index} "
            "has invalid "
            "development dates."
        )

        assert (
            development_end
            <= validation_start
        ), (
            f"Window {index} "
            "development period "
            "overlaps validation."
        )

        assert (
            validation_start
            < validation_end
        ), (
            f"Window {index} "
            "has invalid "
            "validation dates."
        )

        if (
            previous_validation_end
            is not None
        ):
            assert (
                validation_start
                >= previous_validation_end
            ), (
                "Validation windows "
                "are out of "
                "chronological order."
            )

        previous_validation_end = (
            validation_end
        )

    print(
        f"Integrity checks passed "
        f"for {len(windows)} windows."
    )


def extract_report_windows(
    report
):
    windows = report.get(
        "windows"
    )

    if windows is None:
        raise AssertionError(
            "Walk-forward report "
            "does not contain "
            "'windows'."
        )

    if not isinstance(
        windows,
        list,
    ):
        raise AssertionError(
            "Walk-forward report "
            "'windows' must be "
            "a list."
        )

    return windows


def collect_window_variant_trades(
    window,
    variant_name,
):
    validation_results = (
        get_validation_results(
            window
        )
    )

    if validation_results is None:
        return []

    if isinstance(
        validation_results,
        dict,
    ):
        variant_result = (
            validation_results.get(
                variant_name
            )
        )

        if variant_result is None:
            return []

        return normalize_trades(
            variant_result
        )

    if isinstance(
        validation_results,
        list,
    ):
        collected = []

        for item in validation_results:
            if not isinstance(
                item,
                dict,
            ):
                continue

            if (
                item.get(
                    "variant"
                )
                == variant_name
            ):
                collected.append(
                    item
                )

        return collected

    return []


def print_basic_walk_forward_summary(
    report
):
    print(
        "\n5. BASIC WALK-FORWARD SUMMARY"
    )
    print("-" * 120)

    windows = extract_report_windows(
        report
    )

    for index, window in enumerate(
        windows,
        start=1,
    ):
        (
            development_start,
            development_end,
            validation_start,
            validation_end,
        ) = extract_window_dates(
            window
        )

        print(
            f"\nWindow {index}"
        )

        print(
            f"  Development: "
            f"{development_start} "
            f"-> {development_end}"
        )

        print(
            f"  Validation : "
            f"{validation_start} "
            f"-> {validation_end}"
        )

        for variant in VARIANTS:
            trades = (
                collect_window_variant_trades(
                    window,
                    variant,
                )
            )

            summary = summarize_trades(
                trades
            )

            print(
                f"  {variant:<35} "
                f"trades={summary['trades']:>3} "
                f"win={summary['win_rate'] * 100:>6.2f}% "
                f"PF={summary['profit_factor']:>8.4f} "
                f"P&L={summary['total_pnl']:>10.2f}"
            )


def print_target_regime_analysis(
    report
):
    print(
        "\n6. TARGET-REGIME ANALYSIS"
    )
    print("=" * 120)

    windows = extract_report_windows(
        report
    )

    for (
        group_name,
        columns,
        values,
    ) in TARGET_GROUPS:

        print(
            f"\nTARGET: "
            f"{group_name}"
        )

        print(
            "-" * 120
        )

        for variant in VARIANTS:
            print(
                f"\n{variant}"
            )

            aggregate_trades = []

            for index, window in enumerate(
                windows,
                start=1,
            ):
                trades = (
                    collect_window_variant_trades(
                        window,
                        variant,
                    )
                )

                matching = [
                    trade
                    for trade in trades
                    if trade_matches_group(
                        trade,
                        columns,
                        values,
                    )
                ]

                aggregate_trades.extend(
                    matching
                )

                summary = summarize_trades(
                    matching
                )

                (
                    _development_start,
                    _development_end,
                    validation_start,
                    validation_end,
                ) = extract_window_dates(
                    window
                )

                print(
                    f"  Window {index} "
                    f"{validation_start} "
                    f"-> {validation_end} | "
                    f"trades={summary['trades']:>3} "
                    f"win={summary['win_rate'] * 100:>6.2f}% "
                    f"PF={summary['profit_factor']:>8.4f} "
                    f"P&L={summary['total_pnl']:>10.2f}"
                )

            aggregate = summarize_trades(
                aggregate_trades
            )

            print(
                f"  AGGREGATE "
                f"trades={aggregate['trades']:>3} "
                f"win={aggregate['win_rate'] * 100:>6.2f}% "
                f"PF={aggregate['profit_factor']:>8.4f} "
                f"P&L={aggregate['total_pnl']:>10.2f}"
            )


def persistence_status(
    window_summaries
):
    sufficient = [
        summary
        for summary in window_summaries
        if summary["trades"] >= 5
    ]

    if not sufficient:
        return (
            "INSUFFICIENT_DATA"
        )

    positive_pf = sum(
        summary[
            "profit_factor"
        ] > 1.0
        for summary in sufficient
    )

    positive_pnl = sum(
        summary[
            "total_pnl"
        ] > 0
        for summary in sufficient
    )

    negative_pf = sum(
        summary[
            "profit_factor"
        ] < 1.0
        for summary in sufficient
    )

    negative_pnl = sum(
        summary[
            "total_pnl"
        ] < 0
        for summary in sufficient
    )

    total = len(
        sufficient
    )

    if (
        positive_pf == total
        and positive_pnl == total
    ):
        return (
            "PERSISTENT_POSITIVE"
        )

    if (
        negative_pf == total
        and negative_pnl == total
    ):
        return (
            "PERSISTENT_NEGATIVE"
        )

    if (
        positive_pf >= 2
        and positive_pnl >= 2
    ):
        return (
            "MOSTLY_POSITIVE"
        )

    if (
        negative_pf >= 2
        and negative_pnl >= 2
    ):
        return (
            "MOSTLY_NEGATIVE"
        )

    return "MIXED"


def print_persistence_analysis(
    report
):
    print(
        "\n7. PERSISTENCE ANALYSIS"
    )
    print("=" * 120)

    windows = extract_report_windows(
        report
    )

    rows = []

    for (
        group_name,
        columns,
        values,
    ) in TARGET_GROUPS:

        for variant in VARIANTS:
            summaries = []

            for window in windows:
                trades = (
                    collect_window_variant_trades(
                        window,
                        variant,
                    )
                )

                matching = [
                    trade
                    for trade in trades
                    if trade_matches_group(
                        trade,
                        columns,
                        values,
                    )
                ]

                summaries.append(
                    summarize_trades(
                        matching
                    )
                )

            sufficient = [
                summary
                for summary in summaries
                if summary["trades"] >= 5
            ]

            rows.append(
                {
                    "group": group_name,
                    "variant": variant,
                    "status": (
                        persistence_status(
                            summaries
                        )
                    ),
                    "windows_with_data": (
                        len(sufficient)
                    ),
                    "positive_pf_windows": sum(
                        summary[
                            "profit_factor"
                        ] > 1.0
                        for summary
                        in sufficient
                    ),
                    "positive_pnl_windows": sum(
                        summary[
                            "total_pnl"
                        ] > 0
                        for summary
                        in sufficient
                    ),
                }
            )

    for row in rows:
        print(
            f"{row['group']:<42} "
            f"{row['variant']:<35} "
            f"{row['status']:<20} "
            f"data={row['windows_with_data']} "
            f"PF>1={row['positive_pf_windows']} "
            f"PNL>0={row['positive_pnl_windows']}"
        )


def print_focus_findings(
    report
):
    print(
        "\n8. FOCUS FINDINGS"
    )
    print("=" * 120)

    windows = extract_report_windows(
        report
    )

    group_lookup = {
        name: (
            columns,
            values,
        )
        for (
            name,
            columns,
            values,
        ) in TARGET_GROUPS
    }

    focus_groups = [
        "SHORT",
        "TRENDING_DOWN",
        "SHORT + TRENDING_DOWN",
        "TRENDING_DOWN + LOW_VOLATILITY",
        "SHORT + LOW_VOLATILITY",
        "SHORT + TRENDING_DOWN + LOW_VOLATILITY",
    ]

    for group_name in focus_groups:
        columns, values = (
            group_lookup[
                group_name
            ]
        )

        print(
            f"\n{group_name}"
        )

        print(
            "-" * 120
        )

        for variant in VARIANTS:
            summaries = []

            for window in windows:
                trades = (
                    collect_window_variant_trades(
                        window,
                        variant,
                    )
                )

                matching = [
                    trade
                    for trade in trades
                    if trade_matches_group(
                        trade,
                        columns,
                        values,
                    )
                ]

                summaries.append(
                    summarize_trades(
                        matching
                    )
                )

            sufficient = [
                summary
                for summary in summaries
                if summary["trades"] >= 5
            ]

            if not sufficient:
                print(
                    f"  {variant:<35} "
                    f"INSUFFICIENT_DATA"
                )

                continue

            positive_pf = sum(
                summary[
                    "profit_factor"
                ] > 1.0
                for summary in sufficient
            )

            positive_pnl = sum(
                summary[
                    "total_pnl"
                ] > 0
                for summary in sufficient
            )

            negative_pf = sum(
                summary[
                    "profit_factor"
                ] < 1.0
                for summary in sufficient
            )

            negative_pnl = sum(
                summary[
                    "total_pnl"
                ] < 0
                for summary in sufficient
            )

            print(
                f"  {variant:<35} "
                f"windows={len(sufficient)} "
                f"PF>1={positive_pf} "
                f"PNL>0={positive_pnl} "
                f"PF<1={negative_pf} "
                f"PNL<0={negative_pnl}"
            )


def main():
    print(
        "WALK-FORWARD x REGIME ANALYSIS"
    )

    print(
        "=" * 120
    )

    df = load_real_data()

    df = prepare_data(
        df
    )

    engine = create_engine()

    print(
        "\n4. Running chronological "
        "walk-forward validation..."
    )

    report = engine.run(
        df
    )

    windows = report.get(
        "windows",
        [],
    )

    print(
        f"Validation windows: "
        f"{len(windows)}"
    )

    run_integrity_checks(
        report
    )

    print_basic_walk_forward_summary(
        report
    )

    print_target_regime_analysis(
        report
    )

    print_persistence_analysis(
        report
    )

    print_focus_findings(
        report
    )

    print(
        "\n"
        + "=" * 120
    )

    print(
        "WALK-FORWARD x REGIME "
        "ANALYSIS COMPLETE"
    )

    print(
        "=" * 120
    )


if __name__ == "__main__":
    main()