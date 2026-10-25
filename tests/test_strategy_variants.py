from engines.market_data import load_csv
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.strategy_experiment import (
    StrategyExperiment,
    get_standard_variants,
)


DATA_PATH = "data\\xauusd\\raw\\XAUUSD_5m.csv"


def format_number(value):
    if value == float("inf"):
        return "inf"

    if value is None:
        return "N/A"

    return f"{value:.4f}"


def print_variant_summary(summary):
    print(
        f"{summary['variant_name']:<32}"
        f"{summary['trades']:>8}"
        f"{summary['wins']:>8}"
        f"{summary['losses']:>8}"
        f"{summary['win_rate']:>10.2%}"
        f"{format_number(summary['profit_factor']):>12}"
        f"{summary['total_pnl']:>14.2f}"
        f"{summary['max_drawdown']:>11.2%}"
        f"{summary['candidate_blocked_signals']:>10}"
    )


def main():
    print("MULTI-VARIANT STRATEGY EXPERIMENT")
    print("=" * 120)

    print()
    print("1. Loading real XAUUSD data...")

    raw_data = load_csv(DATA_PATH)

    if raw_data is None:
        raise AssertionError(
            "Market-data loader returned None."
        )

    if raw_data.empty:
        raise AssertionError(
            "Market-data file is empty."
        )

    print(
        f"Rows loaded: {len(raw_data)}"
    )

    print()
    print("2. Building technical features...")

    analyzed_data = add_technical_features(
        raw_data.copy()
    )

    print("Technical features added.")

    print()
    print("3. Building market regimes...")

    analyzed_data = add_market_regime(
        analyzed_data
    )

    print("Market regimes added.")

    print()
    print("4. Generating baseline signals...")

    analyzed_data = generate_signals(
        analyzed_data
    )

    baseline_signals = int(
        analyzed_data["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    print(
        f"Baseline executable signals: "
        f"{baseline_signals}"
    )

    if baseline_signals == 0:
        raise AssertionError(
            "No executable baseline signals."
        )

    print()
    print("5. Creating experiment engine...")

    experiment = StrategyExperiment(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        commission_per_trade=0.0,
        slippage_per_trade=0.0,
    )

    print("Experiment engine ready.")

    variants = get_standard_variants()

    results = {}

    print()
    print("6. Running all variants...")
    print("=" * 120)

    for variant_name, transform in variants:

        print(
            f"Running {variant_name}..."
        )

        result = experiment.run_variant(
            analyzed_data=analyzed_data,
            variant_name=variant_name,
            transform=transform,
        )

        summary = (
            StrategyExperiment
            .summarize_result(result)
        )

        results[variant_name] = result

        if summary["trades"] == 0:
            raise AssertionError(
                f"{variant_name} produced zero trades."
            )

    print()
    print(
        f"{'VARIANT':<32}"
        f"{'TRADES':>8}"
        f"{'WINS':>8}"
        f"{'LOSSES':>8}"
        f"{'WIN RATE':>10}"
        f"{'PF':>12}"
        f"{'P&L':>14}"
        f"{'MAX DD':>11}"
        f"{'BLOCKED':>10}"
    )

    print("-" * 120)

    summaries = {}

    for variant_name, _ in variants:

        summary = (
            StrategyExperiment
            .summarize_result(
                results[variant_name]
            )
        )

        summaries[variant_name] = summary

        print_variant_summary(
            summary
        )

    print()
    print("7. Chronological validation...")
    print("=" * 120)

    baseline_result = results[
        "V1_BASELINE"
    ]

    baseline_trades = baseline_result.get(
        "trades",
        [],
    )

    if len(baseline_trades) < 10:
        raise AssertionError(
            "Not enough baseline trades for validation."
        )

    entry_times = []

    for trade in baseline_trades:

        entry_time = (
            experiment
            ._trade_entry_time(trade)
        )

        if entry_time is not None:
            entry_times.append(
                entry_time
            )

    if len(entry_times) < 10:
        raise AssertionError(
            "Not enough timestamped trades."
        )

    entry_times.sort()

    split_index = int(
        len(entry_times) * 0.70
    )

    split_index = max(
        1,
        min(
            split_index,
            len(entry_times) - 1,
        ),
    )

    split_time = entry_times[
        split_index
    ]

    print(
        f"Validation split: {split_time}"
    )

    print()
    print(
        f"{'VARIANT':<32}"
        f"{'VAL TRADES':>12}"
        f"{'VAL WIN':>12}"
        f"{'VAL PF':>12}"
        f"{'VAL P&L':>14}"
        f"{'VAL DD':>12}"
    )

    print("-" * 100)

    validation_reports = {}

    for variant_name, _ in variants:

        validation_report = (
            experiment.evaluate_validation(
                baseline_result=baseline_result,
                candidate_result=results[
                    variant_name
                ],
                split_time=split_time,
            )
        )

        validation_reports[
            variant_name
        ] = validation_report

        candidate_validation = (
            validation_report[
                "candidate"
            ]["validation"]
        )

        candidate_dd = (
            validation_report[
                "candidate"
            ][
                "validation_max_drawdown"
            ]
        )

        print(
            f"{variant_name:<32}"
            f"{candidate_validation['trades']:>12}"
            f"{candidate_validation['win_rate']:>12.2%}"
            f"{format_number(candidate_validation['profit_factor']):>12}"
            f"{candidate_validation['total_pnl']:>14.2f}"
            f"{candidate_dd:>12.2%}"
        )

    print()
    print("8. Comparison against V1...")
    print("=" * 120)

    baseline = summaries[
        "V1_BASELINE"
    ]

    print(
        f"{'VARIANT':<32}"
        f"{'TRADE Δ':>10}"
        f"{'WIN Δ':>10}"
        f"{'PF Δ':>10}"
        f"{'P&L Δ':>14}"
        f"{'DD Δ':>12}"
    )

    print("-" * 90)

    for variant_name, _ in variants:

        if variant_name == "V1_BASELINE":
            continue

        comparison = (
            experiment.compare_results(
                baseline_result=baseline_result,
                candidate_result=results[
                    variant_name
                ],
            )
        )

        changes = comparison[
            "changes"
        ]

        pf_change = changes[
            "profit_factor"
        ]

        if pf_change is None:
            pf_text = "N/A"
        else:
            pf_text = f"{pf_change:+.4f}"

        print(
            f"{variant_name:<32}"
            f"{changes['trades']:>+10}"
            f"{changes['win_rate']:>+10.2%}"
            f"{pf_text:>10}"
            f"{changes['total_pnl']:>+14.2f}"
            f"{changes['max_drawdown']:>+12.2%}"
        )

    print()
    print("9. Validation change versus V1...")
    print("=" * 120)

    baseline_validation = (
        validation_reports[
            "V1_BASELINE"
        ]["candidate"]["validation"]
    )

    baseline_validation_dd = (
        validation_reports[
            "V1_BASELINE"
        ]["candidate"][
            "validation_max_drawdown"
        ]
    )

    print(
        f"{'VARIANT':<32}"
        f"{'TRADE Δ':>10}"
        f"{'WIN Δ':>10}"
        f"{'PF Δ':>10}"
        f"{'P&L Δ':>14}"
        f"{'DD Δ':>12}"
    )

    print("-" * 90)

    for variant_name, _ in variants:

        if variant_name == "V1_BASELINE":
            continue

        candidate_validation = (
            validation_reports[
                variant_name
            ]["candidate"]["validation"]
        )

        candidate_dd = (
            validation_reports[
                variant_name
            ]["candidate"][
                "validation_max_drawdown"
            ]
        )

        trade_change = (
            candidate_validation[
                "trades"
            ]
            - baseline_validation[
                "trades"
            ]
        )

        win_change = (
            candidate_validation[
                "win_rate"
            ]
            - baseline_validation[
                "win_rate"
            ]
        )

        pf_change = (
            candidate_validation[
                "profit_factor"
            ]
            - baseline_validation[
                "profit_factor"
            ]
        )

        pnl_change = (
            candidate_validation[
                "total_pnl"
            ]
            - baseline_validation[
                "total_pnl"
            ]
        )

        dd_change = (
            candidate_dd
            - baseline_validation_dd
        )

        print(
            f"{variant_name:<32}"
            f"{trade_change:>+10}"
            f"{win_change:>+10.2%}"
            f"{pf_change:>+10.4f}"
            f"{pnl_change:>+14.2f}"
            f"{dd_change:>+12.2%}"
        )

    print()
    print("10. Experiment integrity checks...")
    print("=" * 120)

    assert (
        len(results)
        == len(variants)
    )

    for variant_name, _ in variants:

        result = results[
            variant_name
        ]

        summary = summaries[
            variant_name
        ]

        assert (
            summary["trades"]
            > 0
        )

        assert (
            len(result.get("trades", []))
            == summary["trades"]
        )

    baseline_result_again = results[
        "V1_BASELINE"
    ]

    baseline_summary_again = (
        StrategyExperiment
        .summarize_result(
            baseline_result_again
        )
    )

    assert (
        baseline_summary_again["trades"]
        == 163
    )

    assert abs(
        baseline_summary_again[
            "total_pnl"
        ] - 453.188087
    ) < 0.01

    print(
        "All six variants executed successfully."
    )

    print(
        "Baseline remains unchanged."
    )

    print(
        "Chronological validation completed."
    )

    print(
        "Experiment integrity checks passed."
    )

    print()
    print(
        "MULTI-VARIANT EXPERIMENT TEST PASSED"
    )


if __name__ == "__main__":
    main()