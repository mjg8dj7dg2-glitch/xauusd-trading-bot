from __future__ import annotations

from engines.paper_monitor import PaperTradingMonitor


def make_trade(
    index: int,
    pnl: float,
    direction: str = "LONG",
    result: str | None = None,
):
    if result is None:
        result = "WIN" if pnl > 0 else "LOSS"

    return {
        "trade_id": index,
        "entry_time": f"2026-01-{(index % 28) + 1:02d} 10:00:00",
        "exit_time": f"2026-01-{(index % 28) + 1:02d} 11:00:00",
        "direction": direction,
        "entry_price": 100.0,
        "exit_price": 101.0 if pnl > 0 else 99.0,
        "quantity": 1.0,
        "pnl": pnl,
        "result": result,
    }


def make_report(
    *,
    trade_count: int,
    wins: int,
    profit_factor: float,
    total_pnl: float,
    max_drawdown: float,
    blocked_entries: int = 0,
    strategy_name: str = "TEST_STRATEGY",
    interleave_results: bool = False,
):
    losses = trade_count - wins

    trades = []

    if wins > 0:
        winning_pnl = (
            total_pnl
            * profit_factor
            / (profit_factor + 1.0)
            if profit_factor > 0
            else 1.0
        )

        if winning_pnl <= 0:
            winning_pnl = 100.0

        losing_pnl = winning_pnl - total_pnl

        if losses > 0:
            per_win = winning_pnl / wins
            per_loss = -losing_pnl / losses
        else:
            per_win = total_pnl / wins
            per_loss = 0.0

        if interleave_results:
            win_remaining = wins
            loss_remaining = losses
            trade_index = 1

            while win_remaining > 0 or loss_remaining > 0:
                if win_remaining > 0:
                    trades.append(
                        make_trade(
                            index=trade_index,
                            pnl=per_win,
                            direction="LONG",
                            result="WIN",
                        )
                    )
                    trade_index += 1
                    win_remaining -= 1

                if loss_remaining > 0:
                    trades.append(
                        make_trade(
                            index=trade_index,
                            pnl=-per_loss,
                            direction="SHORT",
                            result="LOSS",
                        )
                    )
                    trade_index += 1
                    loss_remaining -= 1

        else:
            for i in range(wins):
                trades.append(
                    make_trade(
                        index=i + 1,
                        pnl=per_win,
                        direction="LONG",
                        result="WIN",
                    )
                )

            for i in range(losses):
                trades.append(
                    make_trade(
                        index=wins + i + 1,
                        pnl=-per_loss,
                        direction="SHORT",
                        result="LOSS",
                    )
                )

    else:
        per_loss = abs(total_pnl) / max(losses, 1)

        for i in range(losses):
            trades.append(
                make_trade(
                    index=i + 1,
                    pnl=-per_loss,
                    direction="SHORT",
                    result="LOSS",
                )
            )

    return {
        "status": "COMPLETE",
        "strategy_name": strategy_name,
        "mode": "PAPER",
        "live_trading": False,
        "performance": {
            "total_trades": trade_count,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": wins / trade_count if trade_count else 0.0,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "maximum_drawdown": max_drawdown,
        },
        "account": {
            "initial_balance": 10000.0,
            "final_balance": 10000.0 + total_pnl,
        },
        "risk": {
            "blocked_entries": blocked_entries,
            "allowed_entries": trade_count,
            "executed_trades": trade_count,
            "risk_events": [],
        },
        "trades": trades,
        "equity_curve": [],
        "risk_events": [],
    }


def test_insufficient_data():
    monitor = PaperTradingMonitor(minimum_trades=20)

    report = make_report(
        trade_count=10,
        wins=5,
        profit_factor=1.5,
        total_pnl=100.0,
        max_drawdown=0.03,
    )

    result = monitor.evaluate(report)

    assert result["status"] == "INSUFFICIENT_DATA"

    print("PASS: insufficient paper data detected")


def test_healthy_paper_trading():
    monitor = PaperTradingMonitor(
        minimum_trades=20,
        healthy_profit_factor=1.10,
        warning_profit_factor=1.00,
        healthy_win_rate=0.35,
        warning_win_rate=0.30,
        maximum_drawdown=0.10,
        warning_drawdown=0.07,
        maximum_losing_streak=7,
    )

    report = make_report(
        trade_count=20,
        wins=10,
        profit_factor=1.50,
        total_pnl=250.0,
        max_drawdown=0.03,
        interleave_results=True,
    )

    result = monitor.evaluate(report)

    assert result["status"] == "HEALTHY", (
        f"Expected HEALTHY but received {result['status']}. "
        f"Reasons: {result.get('reasons')}. "
        f"Warnings: {result.get('warnings')}."
    )

    print("PASS: healthy paper trading detected")


def test_warning_state():
    monitor = PaperTradingMonitor()

    report = make_report(
        trade_count=20,
        wins=7,
        profit_factor=1.05,
        total_pnl=50.0,
        max_drawdown=0.08,
        interleave_results=True,
    )

    result = monitor.evaluate(report)

    assert result["status"] == "WARNING", (
        f"Expected WARNING but received {result['status']}. "
        f"Reasons: {result.get('reasons')}. "
        f"Warnings: {result.get('warnings')}."
    )

    print("PASS: warning state detected")


def test_paused_state():
    monitor = PaperTradingMonitor()

    report = make_report(
        trade_count=20,
        wins=5,
        profit_factor=0.70,
        total_pnl=-150.0,
        max_drawdown=0.12,
    )

    result = monitor.evaluate(report)

    assert result["status"] == "PAUSED", (
        f"Expected PAUSED but received {result['status']}. "
        f"Reasons: {result.get('reasons')}. "
        f"Warnings: {result.get('warnings')}."
    )

    print("PASS: paused state detected")


def test_regime_warning():
    monitor = PaperTradingMonitor()

    report = make_report(
        trade_count=20,
        wins=10,
        profit_factor=1.50,
        total_pnl=250.0,
        max_drawdown=0.03,
        interleave_results=True,
    )

    regime_report = {
        "direction": {
            "status": "WEAK",
        }
    }

    result = monitor.evaluate(
        paper_report=report,
        regime_report=regime_report,
    )

    assert result["status"] == "WARNING", (
        f"Expected WARNING but received {result['status']}. "
        f"Reasons: {result.get('reasons')}. "
        f"Warnings: {result.get('warnings')}."
    )

    print("PASS: regime weakness detected")


def main():
    print("PAPER TRADING MONITOR TEST")
    print("==========================")

    test_insufficient_data()
    test_healthy_paper_trading()
    test_warning_state()
    test_paused_state()
    test_regime_warning()

    print()
    print("PAPER TRADING MONITOR TEST PASSED")


if __name__ == "__main__":
    main()