from pathlib import Path

import pandas as pd

from engines.paper_runner import PaperTradingRunner


DATA_FILE = Path("data/xauusd/raw/XAUUSD_5m.csv")


def find_column(df: pd.DataFrame, candidates, required=True):
    """
    Find the first matching column using case-insensitive names.
    """
    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        key = candidate.strip().lower()

        if key in normalized:
            return normalized[key]

    if required:
        raise ValueError(
            f"Could not find any of {candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    return None


def build_v5_transform():
    """
    V5:

    1. Block SHORT + ATR_8_12
    2. Block LOW_VOLATILITY + Thursday

    Blocked signals become NO_SIGNAL because that is the
    paper engine's supported representation of no trade.
    """

    def transform(df):
        result = df.copy()

        signal_col = find_column(
            result,
            ["signal"],
        )

        volatility_col = find_column(
            result,
            [
                "volatility_regime",
                "volatility",
                "volatility_class",
            ],
        )

        atr_col = find_column(
            result,
            ["atr"],
        )

        timestamp_col = find_column(
            result,
            [
                "datetime",
                "timestamp",
                "time",
                "date",
            ],
        )

        signal = (
            result[signal_col]
            .astype(str)
            .str.upper()
        )

        volatility = (
            result[volatility_col]
            .astype(str)
            .str.upper()
        )

        atr = pd.to_numeric(
            result[atr_col],
            errors="coerce",
        )

        timestamp = pd.to_datetime(
            result[timestamp_col],
            errors="coerce",
            utc=True,
        )

        # Recreate the ATR_8_12 bucket.
        atr_8_12 = atr.between(
            8,
            12,
            inclusive="left",
        )

        thursday = timestamp.dt.day_name().eq(
            "Thursday"
        )

        block_short_atr = (
            signal.eq("SHORT")
            & atr_8_12
        )

        block_low_vol_thursday = (
            volatility.eq("LOW_VOLATILITY")
            & thursday
        )

        blocked = (
            block_short_atr
            | block_low_vol_thursday
        )

        result.loc[
            blocked,
            signal_col,
        ] = "NO_SIGNAL"

        return result

    return transform


def build_v7_transform():
    """
    V7 = V5 + block all remaining LONG/SHORT signals
    occurring on Tuesday or Wednesday.

    All blocked trades become NO_SIGNAL.
    """

    v5_transform = build_v5_transform()

    def transform(df):
        result = v5_transform(df)

        signal_col = find_column(
            result,
            ["signal"],
        )

        timestamp_col = find_column(
            result,
            [
                "datetime",
                "timestamp",
                "time",
                "date",
            ],
        )

        timestamp = pd.to_datetime(
            result[timestamp_col],
            errors="coerce",
            utc=True,
        )

        signal = (
            result[signal_col]
            .astype(str)
            .str.upper()
        )

        tuesday_or_wednesday = (
            timestamp.dt.day_name().isin(
                [
                    "Tuesday",
                    "Wednesday",
                ]
            )
        )

        remaining_trade = signal.isin(
            [
                "LONG",
                "SHORT",
            ]
        )

        blocked = (
            tuesday_or_wednesday
            & remaining_trade
        )

        result.loc[
            blocked,
            signal_col,
        ] = "NO_SIGNAL"

        return result

    return transform


def extract_metrics(result):
    """
    Extract the important metrics without assuming
    one exact result schema.
    """

    backtest = result.get(
        "backtest",
        {},
    )

    evaluation = result.get(
        "evaluation",
        {},
    )

    metrics = {}

    sources = [
        evaluation,
        backtest,
        result,
    ]

    keys = [
        "final_balance",
        "profit",
        "pnl",
        "max_drawdown",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "profit_factor",
    ]

    for key in keys:
        for source in sources:
            if isinstance(source, dict) and key in source:
                metrics[key] = source[key]
                break

    return metrics


def run_case(
    label,
    commission_per_trade,
    slippage_per_trade,
):
    print()
    print("=" * 72)
    print(label)
    print("=" * 72)

    print(
        f"Commission per trade : "
        f"{commission_per_trade:.4f}"
    )

    print(
        f"Slippage per trade   : "
        f"{slippage_per_trade:.4f}"
    )

    runner = PaperTradingRunner(
        initial_balance=10000.0,
        strategy_name=(
            f"XAUUSD_V7_ROBUSTNESS_{label}"
        ),
        commission_per_trade=(
            commission_per_trade
        ),
        slippage_per_trade=(
            slippage_per_trade
        ),
    )

    result = runner.run(
        str(DATA_FILE),
        strategy_transform=(
            build_v7_transform()
        ),
    )

    metrics = extract_metrics(result)

    print()
    print("RESULT")
    print("-" * 72)

    for key, value in metrics.items():
        print(
            f"{key:20s}: {value}"
        )

    return result


def main():
    print("=" * 72)
    print("V7 ROBUSTNESS TEST")
    print("=" * 72)

    print()
    print(
        f"Data file: {DATA_FILE}"
    )

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Could not find data file: "
            f"{DATA_FILE}"
        )

    cases = [
        (
            "BASE",
            0.0,
            0.0,
        ),
        (
            "LOW_COST",
            0.5,
            0.5,
        ),
        (
            "MED_COST",
            1.0,
            1.0,
        ),
        (
            "STRESS",
            2.0,
            2.0,
        ),
    ]

    results = {}

    for (
        label,
        commission,
        slippage,
    ) in cases:

        results[label] = run_case(
            label,
            commission,
            slippage,
        )

    print()
    print("=" * 72)
    print("ROBUSTNESS SUMMARY")
    print("=" * 72)

    for label, result in results.items():

        metrics = extract_metrics(
            result
        )

        print()
        print(label)
        print("-" * 72)

        for key in [
            "final_balance",
            "profit",
            "pnl",
            "max_drawdown",
            "trades",
            "wins",
            "losses",
            "win_rate",
            "profit_factor",
        ]:

            if key in metrics:
                print(
                    f"{key:20s}: "
                    f"{metrics[key]}"
                )

    print()
    print("=" * 72)
    print("TEST COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()