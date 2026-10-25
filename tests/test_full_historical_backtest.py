import os
import tempfile

import pandas as pd

from engines.pipeline import TradingPipeline


def create_test_csv(file_path):
    rows = []

    price = 2000.0

    for index in range(400):
        timestamp = (
            pd.Timestamp("2025-01-01")
            + pd.Timedelta(hours=index)
        )

        cycle = index % 80

        if cycle < 40:
            movement = 2.0
        else:
            movement = -2.0

        open_price = price
        close_price = price + movement

        high_price = max(
            open_price,
            close_price,
        ) + 5.0

        low_price = min(
            open_price,
            close_price,
        ) - 5.0

        rows.append(
            {
                "timestamp": timestamp,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": 1000,
            }
        )

        price = close_price

    pd.DataFrame(rows).to_csv(
        file_path,
        index=False,
    )


def count_risk_events(risk_events):
    blocked = 0
    allowed = 0

    for event in risk_events:
        action = str(
            event.get("action", "")
        ).upper()

        if action == "BLOCKED":
            blocked += 1

        elif action == "ENTRY_ALLOWED":
            allowed += 1

    return blocked, allowed


def main():
    print(
        "\nStarting full historical backtest diagnostic..."
    )

    pipeline = TradingPipeline(
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        minimum_rows=100,
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        file_path = os.path.join(
            temp_dir,
            "xauusd_full_test.csv",
        )

        create_test_csv(file_path)

        print(
            f"\nTest CSV created: {file_path}"
        )

        result = pipeline.run(
            file_path=file_path
        )

        analyzed_data = result["data"]
        backtest = result["backtest"]
        report = result["report"]

        print(
            "\nHistorical analysis completed."
        )

        print(
            f"  Analyzed rows     : "
            f"{len(analyzed_data)}"
        )

        print("\nSignal counts:")

        print(
            analyzed_data[
                "signal"
            ].value_counts()
        )

        print("\nTrend regimes:")

        print(
            analyzed_data[
                "trend_regime"
            ].value_counts()
        )

        print("\nVolatility regimes:")

        print(
            analyzed_data[
                "volatility_regime"
            ].value_counts()
        )

        risk_events = backtest.get(
            "risk_events",
            [],
        )

        blocked_entries, allowed_entries = (
            count_risk_events(
                risk_events
            )
        )

        executed_trades = len(
            backtest.get(
                "trades",
                [],
            )
        )

        print("\nBacktest result:")

        print(
            f"  Initial balance   : "
            f"{backtest['initial_balance']}"
        )

        print(
            f"  Final balance     : "
            f"{backtest['final_balance']}"
        )

        print(
            f"  Total trades      : "
            f"{backtest['total_trades']}"
        )

        print(
            f"  Winning trades    : "
            f"{backtest['winning_trades']}"
        )

        print(
            f"  Losing trades     : "
            f"{backtest['losing_trades']}"
        )

        print(
            f"  Win rate          : "
            f"{backtest['win_rate']}"
        )

        print(
            f"  Profit factor     : "
            f"{backtest['profit_factor']}"
        )

        print(
            f"  Max drawdown      : "
            f"{backtest['max_drawdown']}"
        )

        print(
            f"  Risk events       : "
            f"{len(risk_events)}"
        )

        print(
            f"  Blocked entries   : "
            f"{blocked_entries}"
        )

        print(
            f"  Allowed entries   : "
            f"{allowed_entries}"
        )

        print(
            f"  Executed trades   : "
            f"{executed_trades}"
        )

        print(
            "\nChecking pipeline outputs..."
        )

        assert "data" in result
        assert "analysis" in result
        assert "backtest" in result
        assert "report" in result

        print(
            "  All major pipeline outputs exist."
        )

        print(
            "\nChecking analyzed data..."
        )

        required_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "sma",
            "ema",
            "rsi",
            "atr",
            "volatility",
            "volatility_regime",
            "trend_regime",
            "signal",
            "signal_strength",
            "signal_reason",
        ]

        for column in required_columns:
            assert column in analyzed_data.columns, (
                f"Missing column: {column}"
            )

        print(
            "  Required analysis columns exist."
        )

        print(
            "\nChecking backtest structure..."
        )

        assert (
            backtest["initial_balance"]
            == 10000.0
        )

        assert "trades" in backtest
        assert "risk_events" in backtest
        assert "equity_curve" in backtest

        assert (
            backtest["total_trades"]
            == len(backtest["trades"])
        )

        assert (
            executed_trades
            == backtest["total_trades"]
        )

        assert (
            blocked_entries
            + allowed_entries
            == len(risk_events)
        )

        print(
            "  Backtest structure is valid."
        )

        print(
            "\nChecking risk-event structure..."
        )

        for event in risk_events:
            assert "timestamp" in event
            assert "signal" in event
            assert "action" in event

        print(
            "  Risk-event structure is valid."
        )

        print(
            "\nChecking equity curve..."
        )

        equity_curve = backtest[
            "equity_curve"
        ]

        assert len(equity_curve) > 0

        print(
            f"  Equity curve points: "
            f"{len(equity_curve)}"
        )

        print(
            "\nChecking report..."
        )

        assert "analysis" in report
        assert "backtest" in report

        assert (
            report["analysis"]["rows"]
            == 400
        )

        print(
            "  Research report is valid."
        )

    print(
        "\nFULL HISTORICAL BACKTEST TEST PASSED"
    )


if __name__ == "__main__":
    main()