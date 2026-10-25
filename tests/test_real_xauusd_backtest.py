import os

from engines.pipeline import TradingPipeline


DATA_FILE = os.path.join(
    "data",
    "xauusd",
    "raw",
    "XAUUSD_5m.csv",
)


def main():
    print("\nStarting REAL XAUUSD BACKTEST...")

    print(
        f"\nDataset:\n"
        f"  {os.path.abspath(DATA_FILE)}"
    )

    if not os.path.exists(DATA_FILE):
        print(
            "\nERROR: XAUUSD dataset was not found."
        )
        return

    pipeline = TradingPipeline(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        minimum_rows=100,
    )

    print(
        "\nRunning complete real-data backtest..."
    )

    result = pipeline.run(
        file_path=DATA_FILE
    )

    data = result["data"]
    backtest = result["backtest"]
    report = result["report"]

    trades = backtest.get(
        "trades",
        [],
    )

    risk_events = backtest.get(
        "risk_events",
        [],
    )

    blocked = sum(
        1
        for event in risk_events
        if str(
            event.get("action", "")
        ).upper()
        == "BLOCKED"
    )

    allowed = sum(
        1
        for event in risk_events
        if str(
            event.get("action", "")
        ).upper()
        == "ENTRY_ALLOWED"
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "REAL XAUUSD BACKTEST RESULTS"
    )

    print(
        "=" * 70
    )

    print(
        f"\nData rows          : {len(data)}"
    )

    print(
        f"Initial balance    : "
        f"{backtest['initial_balance']:.2f}"
    )

    print(
        f"Final balance      : "
        f"{backtest['final_balance']:.2f}"
    )

    print(
        f"Total trades       : "
        f"{backtest['total_trades']}"
    )

    print(
        f"Winning trades     : "
        f"{backtest['winning_trades']}"
    )

    print(
        f"Losing trades      : "
        f"{backtest['losing_trades']}"
    )

    print(
        f"Win rate           : "
        f"{backtest['win_rate']:.4f}"
    )

    print(
        f"Profit factor      : "
        f"{backtest['profit_factor']}"
    )

    print(
        f"Maximum drawdown   : "
        f"{backtest['max_drawdown']}"
    )

    print(
        f"Risk events        : "
        f"{len(risk_events)}"
    )

    print(
        f"Blocked entries    : "
        f"{blocked}"
    )

    print(
        f"Allowed entries    : "
        f"{allowed}"
    )

    print(
        f"Executed trades    : "
        f"{len(trades)}"
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "TRADE OUTCOMES"
    )

    print(
        "=" * 70
    )

    if not trades:
        print(
            "\nNo completed trades were produced."
        )

    else:
        for index, trade in enumerate(
            trades,
            start=1,
        ):
            print(
                f"\nTrade {index}"
            )

            print(
                f"  Direction : "
                f"{trade.get('signal')}"
            )

            print(
                f"  Entry     : "
                f"{trade.get('entry_time')}"
            )

            print(
                f"  Exit      : "
                f"{trade.get('exit_time')}"
            )

            print(
                f"  Entry px  : "
                f"{trade.get('entry_price')}"
            )

            print(
                f"  Exit px   : "
                f"{trade.get('exit_price')}"
            )

            print(
                f"  Quantity  : "
                f"{trade.get('quantity')}"
            )

            print(
                f"  P&L       : "
                f"{trade.get('pnl')}"
            )

            print(
                f"  Exit reason: "
                f"{trade.get('exit_reason')}"
            )

    print(
        "\n" + "=" * 70
    )

    print(
        "STRATEGY HEALTH"
    )

    print(
        "=" * 70
    )

    strategy_health = report.get(
        "strategy_health",
        {},
    )

    recent_health = strategy_health.get(
        "recent",
        {},
    )

    historical_health = strategy_health.get(
        "historical",
        {},
    )

    print(
        f"\nStatus: "
        f"{strategy_health.get('status')}"
    )

    print(
        f"\nRecent performance:"
    )

    print(
        f"  Trades       : "
        f"{recent_health.get('trades')}"
    )

    print(
        f"  Win rate     : "
        f"{recent_health.get('win_rate')}"
    )

    print(
        f"  Profit factor: "
        f"{recent_health.get('profit_factor')}"
    )

    print(
        f"  Total P&L    : "
        f"{recent_health.get('total_pnl')}"
    )

    print(
        f"  Max drawdown : "
        f"{recent_health.get('max_drawdown')}"
    )

    print(
        f"\nHistorical performance:"
    )

    print(
        f"  Trades       : "
        f"{historical_health.get('trades')}"
    )

    print(
        f"  Win rate     : "
        f"{historical_health.get('win_rate')}"
    )

    print(
        f"  Profit factor: "
        f"{historical_health.get('profit_factor')}"
    )

    print(
        f"  Total P&L    : "
        f"{historical_health.get('total_pnl')}"
    )

    print(
        f"  Max drawdown : "
        f"{historical_health.get('max_drawdown')}"
    )

    print(
        f"\nWin-rate change: "
        f"{strategy_health.get('win_rate_change')}"
    )

    print(
        f"Profit-factor change: "
        f"{strategy_health.get('profit_factor_change')}"
    )

    print(
        "\nReason(s):"
    )

    for reason in strategy_health.get(
        "reasons",
        [],
    ):
        print(
            f"  - {reason}"
        )

    print(
        "\n" + "=" * 70
    )

    print(
        "REGIME HEALTH"
    )

    print(
        "=" * 70
    )

    regime_health = report.get(
        "regime_health",
        {},
    )

    for regime, result_data in regime_health.items():

        print(
            f"\n{regime}"
        )

        print(
            f"  Status      : "
            f"{result_data.get('status')}"
        )

        metrics = result_data.get(
            "metrics",
            result_data.get(
                "performance",
                result_data,
            ),
        )

        if not isinstance(metrics, dict):
            metrics = {}

        print(
            f"  Trades      : "
            f"{metrics.get('trades')}"
        )

        print(
            f"  Win rate    : "
            f"{metrics.get('win_rate')}"
        )

        print(
            f"  Profit factor: "
            f"{metrics.get('profit_factor')}"
        )

        print(
            f"  Total P&L   : "
            f"{metrics.get('total_pnl')}"
        )

        reasons = result_data.get(
            "reasons",
            [],
        )

        if reasons:
            print(
                "  Reason(s):"
            )

            for reason in reasons:
                print(
                    f"    - {reason}"
                )

    print(
        "\n" + "=" * 70
    )

    print(
        "BACKTEST VALIDATION"
    )

    print(
        "=" * 70
    )

    assert len(data) == 36006

    assert (
        backtest["initial_balance"]
        == 10000.0
    )

    assert (
        backtest["total_trades"]
        == len(trades)
    )

    assert (
        backtest["winning_trades"]
        + backtest["losing_trades"]
        == backtest["total_trades"]
    )

    assert (
        blocked + allowed
        == len(risk_events)
    )

    assert (
        len(backtest["equity_curve"])
        == len(data)
    )

    assert (
        "status" in strategy_health
    )

    assert (
        "recent" in strategy_health
    )

    assert (
        "historical" in strategy_health
    )

    assert (
        len(regime_health) > 0
    )

    print(
        "\nAll real-data backtest "
        "validation checks passed."
    )

    print(
        "\nREAL XAUUSD BACKTEST TEST PASSED"
    )


if __name__ == "__main__":
    main()