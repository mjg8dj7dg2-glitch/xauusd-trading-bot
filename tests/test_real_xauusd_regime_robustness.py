from pathlib import Path

from engines.pipeline import TradingPipeline
from engines.regime_robustness import RegimeRobustnessAnalyzer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "xauusd" / "raw" / "XAUUSD_5m.csv"


def print_regime_names(title, values):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    if not values:
        print("None found.")
        return

    for value in values:
        print(f"- {value}")


def main():
    print("=" * 80)
    print("REAL XAUUSD REGIME ROBUSTNESS ANALYSIS")
    print("=" * 80)

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"XAUUSD CSV not found:\n{CSV_PATH}"
        )

    pipeline = TradingPipeline(
        initial_balance=10_000.0
    )

    result = pipeline.run(
        str(CSV_PATH)
    )

    if not isinstance(result, dict):
        raise TypeError(
            "TradingPipeline.run() must return a dictionary."
        )

    backtest = result.get("backtest")

    if not isinstance(backtest, dict):
        raise ValueError(
            "Pipeline result does not contain a 'backtest' dictionary."
        )

    trades = backtest.get("trades", [])

    if not isinstance(trades, list):
        raise TypeError(
            f"Expected backtest['trades'] to be a list, got {type(trades)}"
        )

    if not trades:
        raise ValueError(
            "No completed trades were produced by the real XAUUSD backtest."
        )

    print()
    print(f"Data file : {CSV_PATH}")
    print(f"Trades    : {len(trades)}")

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=5
    )

    report = analyzer.analyze_all(trades)

    print()
    print("=" * 80)
    print("REGIME ROBUSTNESS REPORT")
    print("=" * 80)

    analyzer.print_report(trades)

    weak = analyzer.find_weak_regimes(trades)
    positive = analyzer.find_positive_regimes(trades)

    print_regime_names(
        "WEAK REGIMES",
        weak
    )

    print_regime_names(
        "POSITIVE REGIMES",
        positive
    )

    print()
    print("=" * 80)
    print("KEY REAL-DATA FINDINGS")
    print("=" * 80)

    # Pull the detailed analyses directly from the report.
    direction = report["direction"]
    trend_and_volatility = report["trend_and_volatility"]

    print()
    print("Direction:")
    for _, row in direction.iterrows():
        print(
            f"  {row['direction']}: "
            f"{int(row['trades'])} trades, "
            f"win rate {row['win_rate']:.2f}%, "
            f"PF {row['profit_factor']:.4f}, "
            f"P&L {row['total_pnl']:.2f}, "
            f"status {row['status']}"
        )

    print()
    print("Trend + volatility:")
    for _, row in trend_and_volatility.iterrows():
        print(
            f"  {row['trend_regime']} + "
            f"{row['volatility_regime']}: "
            f"{int(row['trades'])} trades, "
            f"win rate {row['win_rate']:.2f}%, "
            f"PF {row['profit_factor']:.4f}, "
            f"P&L {row['total_pnl']:.2f}, "
            f"status {row['status']}"
        )

    print()
    print("=" * 80)
    print("REAL XAUUSD REGIME ROBUSTNESS TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()