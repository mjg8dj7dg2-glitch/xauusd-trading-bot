from pathlib import Path

from engines.pipeline import TradingPipeline
from engines.paper_runner import PaperTradingRunner
from engines.strategy_experiment import (
    block_low_vol_thursday,
    block_short_atr_8_12,
    compose_transforms,
)


DATA_FILE = Path("data/xauusd/raw/XAUUSD_5m.csv")


def build_v5():
    """
    V5 =
        V2: block SHORT trades when ATR is 8-12
        +
        V3: block trades on Thursday during LOW volatility
    """
    return compose_transforms(
        block_short_atr_8_12,
        block_low_vol_thursday,
    )


def build_v7():
    """
    V7 =
        V5
        +
        block remaining LONG/SHORT signals
        on Tuesday and Wednesday.
    """

    v5 = build_v5()

    def transform(df):
        result = v5(df)

        tue_wed = result[
            "timestamp"
        ].dt.dayofweek.isin([1, 2])

        mask = (
            result["signal"].isin(
                ["LONG", "SHORT"]
            )
            & tue_wed
        )

        result.loc[
            mask,
            "signal"
        ] = "NO_SIGNAL"

        return result

    return transform


def calculate_trade_statistics(trades):
    """
    Calculate paper-trade statistics directly from
    the actual trade records returned by the paper engine.

    This avoids assuming that paper_report["trades"]
    is an integer count.
    """

    if trades is None:
        trades = []

    if not isinstance(trades, list):
        raise TypeError(
            "Expected paper_report['trades'] to be a list, "
            f"got {type(trades).__name__}"
        )

    total_trades = len(trades)

    wins = 0
    losses = 0
    total_pnl = 0.0

    for trade in trades:
        if not isinstance(trade, dict):
            continue

        result = str(
            trade.get("result", "")
        ).upper()

        pnl_value = trade.get(
            "pnl",
            0.0,
        )

        try:
            pnl = float(
                pnl_value
            )
        except (
            TypeError,
            ValueError,
        ):
            pnl = 0.0

        total_pnl += pnl

        if result == "WIN":
            wins += 1

        elif result == "LOSS":
            losses += 1

    win_rate = (
        wins / total_trades
        if total_trades > 0
        else 0.0
    )

    gross_profit = sum(
        float(
            trade.get("pnl", 0.0)
        )
        for trade in trades
        if isinstance(trade, dict)
        and str(
            trade.get("result", "")
        ).upper() == "WIN"
    )

    gross_loss = sum(
        abs(
            float(
                trade.get("pnl", 0.0)
            )
        )
        for trade in trades
        if isinstance(trade, dict)
        and str(
            trade.get("result", "")
        ).upper() == "LOSS"
    )

    if gross_loss > 0:
        profit_factor = (
            gross_profit
            / gross_loss
        )
    else:
        profit_factor = (
            float("inf")
            if gross_profit > 0
            else 0.0
        )

    average_pnl = (
        total_pnl / total_trades
        if total_trades > 0
        else 0.0
    )

    return {
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "average_pnl": average_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
    }


def calculate_max_drawdown(trades):
    """
    Calculate maximum drawdown from the chronological
    paper-trade P&L sequence.

    This is a fallback calculation used only when the
    report's own max-drawdown field is absent or unusable.
    """

    if not trades:
        return 0.0

    running_pnl = 0.0
    peak = 0.0
    maximum_drawdown = 0.0

    for trade in trades:
        if not isinstance(trade, dict):
            continue

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

        running_pnl += pnl

        if running_pnl > peak:
            peak = running_pnl

        drawdown = peak - running_pnl

        if drawdown > maximum_drawdown:
            maximum_drawdown = drawdown

    return maximum_drawdown


def print_dictionary_summary(
    title,
    value,
):
    print()
    print(title)
    print("-" * len(title))

    if isinstance(value, dict):
        for key, item in value.items():
            print(
                f"{key}: {item}"
            )
    else:
        print(value)


def main():
    print("V7 PAPER TRADING TEST")
    print("=" * 40)

    # =========================================================
    # 1. Load and analyze market data
    # =========================================================
    print()
    print(
        "[1/6] Loading and analyzing XAUUSD data..."
    )

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing data file: {DATA_FILE}"
        )

    pipeline = TradingPipeline()

    pipeline_report = pipeline.run(
        str(DATA_FILE)
    )

    analyzed = pipeline_report["data"]

    print(
        f"PASS: {len(analyzed):,} rows analyzed"
    )

    # =========================================================
    # 2. Verify exact V7 signal filtering
    # =========================================================
    print()
    print(
        "[2/6] Applying exact V7 rules..."
    )

    v5_transform = build_v5()
    v7_transform = build_v7()

    original_data = analyzed.copy()

    v5_data = v5_transform(
        analyzed.copy()
    )

    v7_data = v7_transform(
        analyzed.copy()
    )

    original_signals = int(
        original_data["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    v5_signals = int(
        v5_data["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    v7_signals = int(
        v7_data["signal"]
        .isin(["LONG", "SHORT"])
        .sum()
    )

    v5_blocked = (
        original_signals
        - v5_signals
    )

    v7_blocked = (
        original_signals
        - v7_signals
    )

    additional_v7_blocks = (
        v5_signals
        - v7_signals
    )

    print(
        "Original LONG/SHORT signals : "
        f"{original_signals}"
    )

    print(
        "V5 blocked signals          : "
        f"{v5_blocked}"
    )

    print(
        "V5 remaining signals        : "
        f"{v5_signals}"
    )

    print(
        "V7 blocked signals          : "
        f"{v7_blocked}"
    )

    print(
        "V7 remaining signals        : "
        f"{v7_signals}"
    )

    print(
        "Additional Tue/Wed blocks   : "
        f"{additional_v7_blocks}"
    )

    # Known values established by previous tests.
    if original_signals != 471:
        raise RuntimeError(
            "Unexpected original signal count: "
            f"{original_signals}"
        )

    if v5_blocked != 189:
        raise RuntimeError(
            "Unexpected V5 blocked count: "
            f"{v5_blocked}"
        )

    if v5_signals != 282:
        raise RuntimeError(
            "Unexpected V5 remaining count: "
            f"{v5_signals}"
        )

    if v7_signals != 144:
        raise RuntimeError(
            "Unexpected V7 remaining count: "
            f"{v7_signals}"
        )

    if additional_v7_blocks != 138:
        raise RuntimeError(
            "Unexpected additional V7 blocks: "
            f"{additional_v7_blocks}"
        )

    print(
        "PASS: exact V7 signal filtering verified"
    )

    # =========================================================
    # 3. Run persistent V7 paper trading
    # =========================================================
    print()
    print(
        "[3/6] Running V7 paper trading simulation..."
    )

    runner = PaperTradingRunner(
        initial_balance=10000.0,
        strategy_name="XAUUSD_V7_PAPER_TEST",
    )

    result = runner.run(
        str(DATA_FILE),
        strategy_transform=v7_transform,
    )

    if result["status"] != "COMPLETE":
        raise RuntimeError(
            "Paper runner did not complete. "
            f"Status: {result['status']}"
        )

    print(
        "PASS: V7 paper trading completed"
    )

    # =========================================================
    # 4. Read actual paper report structure
    # =========================================================
    print()
    print(
        "[4/6] Reading V7 paper report..."
    )

    report = result.get(
        "paper_report",
        {},
    )

    if not isinstance(report, dict):
        raise TypeError(
            "paper_report must be a dictionary."
        )

    trades = report.get(
        "trades",
        [],
    )

    statistics = calculate_trade_statistics(
        trades
    )

    # Prefer the engine's own max drawdown when
    # it provides a numeric value.
    raw_max_drawdown = report.get(
        "max_drawdown",
        None,
    )

    try:
        engine_max_drawdown = float(
            raw_max_drawdown
        )
    except (
        TypeError,
        ValueError,
    ):
        engine_max_drawdown = None

    if engine_max_drawdown is not None:
        max_drawdown = engine_max_drawdown
    else:
        max_drawdown = calculate_max_drawdown(
            trades
        )

    final_balance = report.get(
        "final_balance",
        None,
    )

    if final_balance is None:
        final_balance = (
            10000.0
            + statistics["total_pnl"]
        )

    print()
    print(
        "V7 PAPER RESULTS"
    )
    print(
        "-----------------"
    )

    print(
        f"Final balance : "
        f"{float(final_balance):,.2f}"
    )

    print(
        f"P&L           : "
        f"{statistics['total_pnl']:+,.2f}"
    )

    print(
        f"Trades        : "
        f"{statistics['trades']}"
    )

    print(
        f"Wins          : "
        f"{statistics['wins']}"
    )

    print(
        f"Losses        : "
        f"{statistics['losses']}"
    )

    print(
        f"Win rate      : "
        f"{statistics['win_rate']:.2%}"
    )

    pf = statistics["profit_factor"]

    if pf == float("inf"):
        pf_display = "INF"
    else:
        pf_display = f"{pf:.4f}"

    print(
        f"Profit factor : "
        f"{pf_display}"
    )

    print(
        f"Average P&L   : "
        f"{statistics['average_pnl']:+,.2f}"
    )

    print(
        f"Max drawdown  : "
        f"{max_drawdown:.2%}"
    )

    if statistics["trades"] <= 0:
        raise RuntimeError(
            "V7 paper trading produced zero trades."
        )

    print(
        "PASS: paper trade statistics calculated "
        "from actual trade records"
    )

    # =========================================================
    # 5. Verify persistence and monitoring
    # =========================================================
    print()
    print(
        "[5/6] Checking persistence and monitoring..."
    )

    session_id = result.get(
        "session_id"
    )

    session = result.get(
        "session"
    )

    monitor = result.get(
        "monitor"
    )

    record_counts = result.get(
        "record_counts"
    )

    if not session_id:
        raise RuntimeError(
            "Missing V7 paper session ID."
        )

    if not session:
        raise RuntimeError(
            "Missing V7 paper session."
        )

    if not monitor:
        raise RuntimeError(
            "Missing V7 paper monitor result."
        )

    if not record_counts:
        raise RuntimeError(
            "Missing V7 persistence record counts."
        )

    print(
        f"Session ID       : {session_id}"
    )

    print(
        "Persisted trades : "
        f"{record_counts.get('trades', 0)}"
    )

    print(
        "Equity points    : "
        f"{record_counts.get('equity_curve', 0)}"
    )

    print(
        "Risk events      : "
        f"{record_counts.get('risk_events', 0)}"
    )

    print(
        "Monitor snapshots: "
        f"{record_counts.get('monitor_snapshots', 0)}"
    )

    print(
        "PASS: persistence and monitoring verified"
    )

    # =========================================================
    # 6. Paper evaluation
    # =========================================================
    print()
    print(
        "[6/6] V7 paper evaluation"
    )

    print(
        "---------------------------"
    )

    paper_evaluation = result.get(
        "paper_evaluation",
        {},
    )

    evaluation_status = paper_evaluation.get(
        "status",
        "UNKNOWN",
    )

    print(
        "Paper evaluation status: "
        f"{evaluation_status}"
    )

    reasons = paper_evaluation.get(
        "reasons",
        [],
    )

    if reasons:
        print()
        print("Reasons:")

        for reason in reasons:
            print(
                f"  - {reason}"
            )

    warnings = paper_evaluation.get(
        "warnings",
        [],
    )

    if warnings:
        print()
        print("Warnings:")

        for warning in warnings:
            print(
                f"  - {warning}"
            )

    # =========================================================
    # Unified health
    # =========================================================
    unified_health = result.get(
        "unified_health",
        {},
    )

    if unified_health:
        print()
        print(
            "UNIFIED HEALTH"
        )

        print(
            "--------------"
        )

        print(
            f"Status: "
            f"{unified_health.get('status', 'UNKNOWN')}"
        )

        print(
            f"Historical health: "
            f"{unified_health.get('historical_health', 'UNKNOWN')}"
        )

        print(
            f"Lifecycle: "
            f"{unified_health.get('lifecycle', 'UNKNOWN')}"
        )

        print(
            f"Paper health: "
            f"{unified_health.get('paper_health', 'UNKNOWN')}"
        )

    # =========================================================
    # Diagnostic: show available report keys
    # =========================================================
    print()
    print(
        "PAPER REPORT STRUCTURE"
    )

    print(
        "----------------------"
    )

    print(
        "Report keys:"
    )

    for key in sorted(report.keys()):
        value = report[key]

        if isinstance(value, list):
            description = (
                f"list ({len(value)} items)"
            )
        elif isinstance(value, dict):
            description = (
                f"dict ({len(value)} keys)"
            )
        else:
            description = (
                type(value).__name__
            )

        print(
            f"  {key}: {description}"
        )

    # =========================================================
    # Final interpretation
    # =========================================================
    print()
    print(
        "V7 PAPER TEST INTERPRETATION"
    )

    print(
        "-----------------------------"
    )

    print(
        "V7 uses the exact rules that passed "
        "the four-window walk-forward test."
    )

    print(
        "This is simulated paper trading only."
    )

    print(
        "No real-money trades are placed."
    )

    print(
        "A positive result does not automatically "
        "activate V7."
    )

    print()
    print(
        "V7 PAPER TRADING TEST PASSED"
    )


if __name__ == "__main__":
    main()