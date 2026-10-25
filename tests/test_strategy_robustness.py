import pandas as pd

from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.strategy_experiment import StrategyExperiment
from engines.walk_forward import WalkForwardEngine
from engines.strategy_robustness import StrategyRobustnessEngine


DATA_FILE = "data\\xauusd\\raw\\XAUUSD_5m.csv"


def load_real_xauusd():
    df = pd.read_csv(DATA_FILE)

    if "datetime" in df.columns:
        df = df.rename(columns={"datetime": "timestamp"})

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        utc=True,
    )

    df = df.sort_values("timestamp")
    df = df.reset_index(drop=True)

    return df


def main():
    print()
    print("=" * 80)
    print("STRATEGY ROBUSTNESS TEST")
    print("=" * 80)

    df = load_real_xauusd()

    print(f"Raw rows: {len(df)}")

    # ------------------------------------------------------------
    # Build the same analysis pipeline used by the existing system.
    # ------------------------------------------------------------

    analyzed = add_technical_features(df)
    analyzed = add_market_regime(analyzed)
    analyzed = generate_signals(analyzed)

    print(f"Analyzed rows: {len(analyzed)}")
    print(
        f"Signals: "
        f"{(analyzed['signal'] != 'NO_SIGNAL').sum()}"
    )

    # ------------------------------------------------------------
    # Load the existing strategy experiment variants.
    # ------------------------------------------------------------

    experiment = StrategyExperiment()

    variants = experiment.get_standard_variants()

    print(
        f"Strategy variants: {len(variants)}"
    )

    for variant_name, _ in variants:
        print(f" - {variant_name}")

    # ------------------------------------------------------------
    # Run chronological walk-forward testing.
    # ------------------------------------------------------------

    walk_forward = WalkForwardEngine(
        experiment=experiment,
        development_days=70,
        validation_days=28,
        step_days=28,
        minimum_validation_trades=5,
    )

    walk_forward_results = walk_forward.run(
        analyzed_data=analyzed,
        variants=variants,
    )

    print(
        f"Walk-forward windows: "
        f"{len(walk_forward_results['windows'])}"
    )

    # ------------------------------------------------------------
    # Evaluate robustness.
    # ------------------------------------------------------------

    robustness_engine = StrategyRobustnessEngine(
        minimum_total_validation_trades=30,
        minimum_windows=4,
        minimum_windows_with_trades=3,
        minimum_profit_factor=1.05,
        robust_profit_factor=1.15,
        minimum_positive_windows_ratio=0.50,
        robust_positive_windows_ratio=0.75,
        maximum_drawdown_for_robust=0.10,
    )

    report = robustness_engine.build_report(
        walk_forward_results,
        baseline_name="V1_BASELINE",
    )

    robustness_engine.print_report(report)

    print()
    print("=" * 80)
    print("ROBUSTNESS TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()