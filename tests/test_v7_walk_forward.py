from pathlib import Path

from engines.data_source import CSVDataSource
from engines.pipeline import TradingPipeline
from engines.strategy_experiment import (
    block_low_vol_thursday,
    block_short_atr_8_12,
    compose_transforms,
)
from engines.walk_forward import WalkForwardEngine


DATA_FILE = Path("data/xauusd/raw/XAUUSD_5m.csv")


def identity_transform(df):
    return df.copy()


def build_v5():
    return compose_transforms(
        block_short_atr_8_12,
        block_low_vol_thursday,
    )


def build_v7():
    v5 = build_v5()

    def transform(df):
        result = v5(df)

        timestamp = result["timestamp"]

        tue_wed = timestamp.dt.dayofweek.isin([1, 2])

        mask = (
            result["signal"].isin(["LONG", "SHORT"])
            & tue_wed
        )

        result.loc[mask, "signal"] = "NO_SIGNAL"

        return result

    return transform


def print_stats(name, stats):
    print()
    print(name)
    print("-" * len(name))

    print(f"Trades       : {stats.get('trades', 0)}")
    print(f"Wins         : {stats.get('wins', 0)}")
    print(f"Losses       : {stats.get('losses', 0)}")
    print(f"Win rate     : {stats.get('win_rate', 0.0):.2%}")
    print(f"Profit factor: {stats.get('profit_factor', 0.0):.4f}")
    print(f"P&L          : {stats.get('total_pnl', 0.0):+.2f}")
    print(f"Max drawdown : {stats.get('max_drawdown', 0.0):.2%}")


def main():
    print("V7 WALK-FORWARD VALIDATION")
    print("=" * 40)

    # ---------------------------------------------------------
    # 1. Load and analyze data
    # ---------------------------------------------------------
    print()
    print("[1/5] Loading and analyzing XAUUSD data...")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing data file: {DATA_FILE}")

    pipeline = TradingPipeline()
    pipeline_report = pipeline.run(str(DATA_FILE))
    analyzed = pipeline_report["data"]

    print(f"PASS: {len(analyzed):,} rows analyzed")

    # ---------------------------------------------------------
    # 2. Build variants
    # ---------------------------------------------------------
    print()
    print("[2/5] Building V1, V5 and V7 variants...")

    variants = [
        ("V1_BASELINE", identity_transform),
        ("V5_BASELINE", build_v5()),
        ("V7_V5_PLUS_TUE_WED", build_v7()),
    ]

    print("PASS: variants created")

    # ---------------------------------------------------------
    # 3. Run walk-forward
    # ---------------------------------------------------------
    print()
    print("[3/5] Running walk-forward validation...")

    engine = WalkForwardEngine(
        development_days=70,
        validation_days=28,
        step_days=28,
        minimum_validation_trades=5,
    )

    result = engine.run(
        analyzed,
        variants=variants,
    )

    print("PASS: walk-forward validation completed")

    # ---------------------------------------------------------
    # 4. Read individual unseen validation windows
    # ---------------------------------------------------------
    print()
    print("[4/5] Individual unseen validation windows")
    print("-" * 43)

    windows = result["windows"]

    if not windows:
        raise RuntimeError("No walk-forward windows were returned.")

    print(f"Validation windows: {len(windows)}")

    v5_window_stats = []
    v7_window_stats = []

    for window_number, window_data in enumerate(windows, start=1):
        variants_data = window_data["variants"]

        v5 = variants_data["V5_BASELINE"]["validation"]
        v7 = variants_data["V7_V5_PLUS_TUE_WED"]["validation"]

        v5_window_stats.append(v5)
        v7_window_stats.append(v7)

        print()
        print(f"WINDOW {window_number}")
        print("=" * 20)

        print()
        print_stats("V5_BASELINE", v5)

        print()
        print_stats("V7_V5_PLUS_TUE_WED", v7)

    # ---------------------------------------------------------
    # 5. Build aggregate validation statistics directly from
    #    the individual unseen windows.
    #
    #    We deliberately calculate these from the actual
    #    validation dictionaries instead of assuming a particular
    #    aggregate-result schema.
    # ---------------------------------------------------------
    print()
    print("[5/5] Aggregate unseen validation comparison")
    print("-" * 49)

    def aggregate_window_stats(stats_list):
        trades = sum(s.get("trades", 0) for s in stats_list)
        wins = sum(s.get("wins", 0) for s in stats_list)
        losses = sum(s.get("losses", 0) for s in stats_list)
        total_pnl = sum(s.get("total_pnl", 0.0) for s in stats_list)

        gross_profit = 0.0
        gross_loss = 0.0

        for stats in stats_list:
            validation_result = stats.get("_validation_result")

            if isinstance(validation_result, dict):
                gross_profit += validation_result.get("gross_profit", 0.0)
                gross_loss += abs(
                    validation_result.get("gross_loss", 0.0)
                )

        # If gross profit/loss are not exposed, calculate PF from
        # the per-window PF values and trade counts only when possible.
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            # No reliable combined PF available from these fields.
            # Keep it explicit rather than inventing a value.
            profit_factor = None

        win_rate = wins / trades if trades else 0.0

        positive_windows = sum(
            1 for s in stats_list
            if s.get("total_pnl", 0.0) > 0
        )

        pf_positive_windows = sum(
            1 for s in stats_list
            if s.get("profit_factor", 0.0) > 1.0
        )

        worst_window_dd = max(
            (s.get("max_drawdown", 0.0) for s in stats_list),
            default=0.0,
        )

        return {
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "worst_window_drawdown": worst_window_dd,
            "positive_windows": positive_windows,
            "pf_positive_windows": pf_positive_windows,
        }

    # The WalkForwardEngine's validation dictionaries already contain
    # the correct unseen-window statistics. Use those directly.
    def simple_aggregate(stats_list):
        trades = sum(s.get("trades", 0) for s in stats_list)
        wins = sum(s.get("wins", 0) for s in stats_list)
        losses = sum(s.get("losses", 0) for s in stats_list)
        pnl = sum(s.get("total_pnl", 0.0) for s in stats_list)

        win_rate = wins / trades if trades else 0.0

        positive_windows = sum(
            1 for s in stats_list
            if s.get("total_pnl", 0.0) > 0
        )

        pf_windows = sum(
            1 for s in stats_list
            if s.get("profit_factor", 0.0) > 1.0
        )

        worst_dd = max(
            (s.get("max_drawdown", 0.0) for s in stats_list),
            default=0.0,
        )

        return {
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "pnl": pnl,
            "positive_windows": positive_windows,
            "pf_windows": pf_windows,
            "worst_dd": worst_dd,
        }

    v5_aggregate = simple_aggregate(v5_window_stats)
    v7_aggregate = simple_aggregate(v7_window_stats)

    print()
    print("V5_BASELINE")
    print("-----------")
    print(f"Validation trades : {v5_aggregate['trades']}")
    print(f"Validation wins   : {v5_aggregate['wins']}")
    print(f"Validation losses : {v5_aggregate['losses']}")
    print(f"Win rate          : {v5_aggregate['win_rate']:.2%}")
    print(f"Validation P&L    : {v5_aggregate['pnl']:+.2f}")
    print(
        f"Worst window DD   : "
        f"{v5_aggregate['worst_dd']:.2%}"
    )
    print(
        f"PF > 1 windows    : "
        f"{v5_aggregate['pf_windows']}"
    )
    print(
        f"P&L > 0 windows   : "
        f"{v5_aggregate['positive_windows']}"
    )

    print()
    print("V7_V5_PLUS_TUE_WED")
    print("------------------")
    print(f"Validation trades : {v7_aggregate['trades']}")
    print(f"Validation wins   : {v7_aggregate['wins']}")
    print(f"Validation losses : {v7_aggregate['losses']}")
    print(f"Win rate          : {v7_aggregate['win_rate']:.2%}")
    print(f"Validation P&L    : {v7_aggregate['pnl']:+.2f}")
    print(
        f"Worst window DD   : "
        f"{v7_aggregate['worst_dd']:.2%}"
    )
    print(
        f"PF > 1 windows    : "
        f"{v7_aggregate['pf_windows']}"
    )
    print(
        f"P&L > 0 windows   : "
        f"{v7_aggregate['positive_windows']}"
    )

    # ---------------------------------------------------------
    # Comparison
    # ---------------------------------------------------------
    print()
    print("COMPARISON")
    print("----------")

    trade_change = (
        v7_aggregate["trades"]
        - v5_aggregate["trades"]
    )

    pnl_change = (
        v7_aggregate["pnl"]
        - v5_aggregate["pnl"]
    )

    win_rate_change = (
        v7_aggregate["win_rate"]
        - v5_aggregate["win_rate"]
    )

    print(f"Trade count change : {trade_change:+d}")
    print(f"P&L change         : {pnl_change:+.2f}")
    print(
        f"Win-rate change    : "
        f"{win_rate_change:+.2%}"
    )

    # ---------------------------------------------------------
    # V7 decision guidance
    # ---------------------------------------------------------
    print()
    print("V7 WALK-FORWARD INTERPRETATION")
    print("-------------------------------")

    print(
        "V7 must be judged from the unseen validation windows, "
        "not from the full-history in-sample result."
    )

    print(
        "The Tuesday/Wednesday rule is NOT automatically promoted "
        "just because its full-history result was stronger."
    )

    v7_positive_ratio = (
        v7_aggregate["positive_windows"]
        / len(v7_window_stats)
    )

    v7_pf_ratio = (
        v7_aggregate["pf_windows"]
        / len(v7_window_stats)
    )

    print(
        f"V7 positive-window ratio : "
        f"{v7_positive_ratio:.2%}"
    )

    print(
        f"V7 PF>1 window ratio     : "
        f"{v7_pf_ratio:.2%}"
    )

    if (
        v7_positive_ratio >= 0.75
        and v7_pf_ratio >= 0.75
        and v7_aggregate["pnl"] > 0
    ):
        print()
        print(
            "V7 RESULT: promising enough for another validation stage."
        )
        print(
            "Do NOT activate it yet; continue robustness/paper testing."
        )
    else:
        print()
        print(
            "V7 RESULT: not strong enough for promotion."
        )
        print(
            "Keep V5 as the current reference strategy."
        )

    print()
    print("V7 WALK-FORWARD VALIDATION COMPLETE")


if __name__ == "__main__":
    main()