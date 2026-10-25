from __future__ import annotations

from engines.paper_evaluation import PaperSessionEvaluator


def build_trade(
    pnl,
    direction="LONG",
    trend_regime="TRENDING_UP",
    volatility_regime="NORMAL",
):
    return {
        "trade_id": f"T{abs(int(pnl * 100))}",
        "pnl": pnl,
        "direction": direction,
        "trend_regime": trend_regime,
        "volatility_regime": volatility_regime,
    }


def build_report(
    trades,
    initial_balance=10000.0,
    final_balance=None,
    max_drawdown=0.05,
):
    if final_balance is None:
        final_balance = initial_balance + sum(
            trade["pnl"] for trade in trades
        )

    return {
        "strategy_name": "TEST_STRATEGY",
        "mode": "PAPER",
        "live_trading": False,
        "account": {
            "initial_balance": initial_balance,
            "final_balance": final_balance,
        },
        "performance": {
            "max_drawdown": max_drawdown,
        },
        "risk": {
            "blocked_entries": 0,
            "allowed_entries": len(trades),
        },
        "trades": trades,
    }


def test_basic_statistics():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(100),
        build_trade(-50),
        build_trade(75),
        build_trade(-25),
    ]

    report = build_report(trades)

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "INSUFFICIENT_DATA"

    statistics = evaluation["trades"]

    assert statistics["total_trades"] == 4
    assert statistics["winning_trades"] == 2
    assert statistics["losing_trades"] == 2
    assert statistics["win_rate"] == 0.5

    assert statistics["gross_profit"] == 175
    assert statistics["gross_loss"] == 75
    assert statistics["total_pnl"] == 100

    assert statistics["profit_factor"] > 2.3
    assert statistics["average_trade"] == 25
    assert statistics["average_win"] == 87.5
    assert statistics["average_loss"] == -37.5

    print("PASS: basic trade statistics")


def test_losing_streak():
    evaluator = PaperSessionEvaluator(
        losing_streak_review_threshold=5
    )

    trades = [
        build_trade(50),
        build_trade(-10),
        build_trade(-20),
        build_trade(-30),
        build_trade(-40),
        build_trade(-50),
        build_trade(-60),
        build_trade(100),
    ]

    report = build_report(trades)

    evaluation = evaluator.evaluate(report)

    assert evaluation["losing_streak"]["maximum"] == 6
    assert evaluation["losing_streak"]["review_threshold"] == 5

    print("PASS: losing streak detection")


def test_review_status_from_losing_streak():
    evaluator = PaperSessionEvaluator(
        losing_streak_review_threshold=5
    )

    trades = [
        build_trade(20),
        build_trade(20),
        build_trade(20),
        build_trade(-10),
        build_trade(-10),
        build_trade(-10),
        build_trade(-10),
        build_trade(-10),
        build_trade(-10),
        build_trade(20),
    ]

    report = build_report(trades)

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "REVIEW"

    assert (
        "A prolonged losing streak was observed."
        in evaluation["reasons"]
    )

    print("PASS: review status from losing streak")


def test_negative_pnl_review():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(-100),
        build_trade(-50),
        build_trade(20),
        build_trade(-40),
        build_trade(10),
        build_trade(-30),
        build_trade(-20),
        build_trade(15),
        build_trade(-25),
        build_trade(-10),
    ]

    report = build_report(
        trades,
        initial_balance=10000,
        final_balance=9770,
        max_drawdown=0.04,
    )

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "REVIEW"

    assert (
        "Paper-session P&L is negative."
        in evaluation["reasons"]
    )

    assert evaluation["account"]["total_pnl"] == -230
    assert evaluation["account"]["return_pct"] == -2.3

    print("PASS: negative P&L review")


def test_profit_factor_review():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(-100),
        build_trade(-100),
        build_trade(-100),
        build_trade(50),
        build_trade(-50),
        build_trade(25),
        build_trade(25),
        build_trade(-25),
        build_trade(-25),
        build_trade(-25),
    ]

    report = build_report(
        trades,
        initial_balance=10000,
        final_balance=9675,
    )

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "REVIEW"

    assert (
        "Profit factor is below 1.0."
        in evaluation["reasons"]
    )

    assert evaluation["trades"]["profit_factor"] < 1.0

    print("PASS: profit factor review")


def test_direction_analysis():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(100, "LONG"),
        build_trade(50, "LONG"),
        build_trade(-25, "LONG"),
        build_trade(-50, "SHORT"),
        build_trade(-25, "SHORT"),
        build_trade(10, "SHORT"),
    ]

    report = build_report(trades)

    evaluation = evaluator.evaluate(report)

    direction = evaluation["direction"]

    assert "LONG" in direction
    assert "SHORT" in direction

    assert direction["LONG"]["total_trades"] == 3
    assert direction["LONG"]["winning_trades"] == 2
    assert direction["LONG"]["losing_trades"] == 1

    assert direction["SHORT"]["total_trades"] == 3
    assert direction["SHORT"]["winning_trades"] == 1
    assert direction["SHORT"]["losing_trades"] == 2

    print("PASS: direction analysis")


def test_regime_analysis():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(
            100,
            "LONG",
            "TRENDING_UP",
            "NORMAL",
        ),
        build_trade(
            50,
            "LONG",
            "TRENDING_UP",
            "NORMAL",
        ),
        build_trade(
            -25,
            "LONG",
            "TRENDING_DOWN",
            "HIGH",
        ),
        build_trade(
            -30,
            "SHORT",
            "TRENDING_DOWN",
            "HIGH",
        ),
        build_trade(
            20,
            "SHORT",
            "RANGE",
            "LOW",
        ),
    ]

    report = build_report(trades)

    evaluation = evaluator.evaluate(report)

    regime = evaluation["regime"]

    assert "TRENDING_UP" in regime["trend"]
    assert "TRENDING_DOWN" in regime["trend"]
    assert "RANGE" in regime["trend"]

    assert "NORMAL" in regime["volatility"]
    assert "HIGH" in regime["volatility"]
    assert "LOW" in regime["volatility"]

    assert (
        regime["trend"]["TRENDING_UP"]["total_pnl"]
        == 150
    )

    assert (
        regime["volatility"]["HIGH"]["total_pnl"]
        == -55
    )

    print("PASS: trend and volatility regime analysis")


def test_recurring_patterns():
    evaluator = PaperSessionEvaluator(
        minimum_trades_for_regime_analysis=3
    )

    trades = [
        build_trade(
            -50,
            "SHORT",
            "TRENDING_DOWN",
            "LOW",
        ),
        build_trade(
            -40,
            "SHORT",
            "TRENDING_DOWN",
            "LOW",
        ),
        build_trade(
            -30,
            "SHORT",
            "TRENDING_DOWN",
            "LOW",
        ),
        build_trade(
            100,
            "LONG",
            "TRENDING_UP",
            "NORMAL",
        ),
        build_trade(
            80,
            "LONG",
            "TRENDING_UP",
            "NORMAL",
        ),
        build_trade(
            60,
            "LONG",
            "TRENDING_UP",
            "NORMAL",
        ),
    ]

    report = build_report(trades)

    evaluation = evaluator.evaluate(report)

    patterns = evaluation["patterns"]

    assert len(patterns["worst"]) >= 1
    assert len(patterns["best"]) >= 1

    worst = patterns["worst"][0]
    best = patterns["best"][0]

    assert worst["direction"] == "SHORT"
    assert worst["trend_regime"] == "TRENDING_DOWN"
    assert worst["volatility_regime"] == "LOW"
    assert worst["total_pnl"] == -120

    assert best["direction"] == "LONG"
    assert best["trend_regime"] == "TRENDING_UP"
    assert best["volatility_regime"] == "NORMAL"
    assert best["total_pnl"] == 240

    print("PASS: recurring pattern analysis")


def test_stable_observation():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(50),
        build_trade(-10),
        build_trade(40),
        build_trade(-5),
        build_trade(60),
        build_trade(-10),
        build_trade(45),
        build_trade(-5),
        build_trade(30),
        build_trade(20),
    ]

    report = build_report(
        trades,
        initial_balance=10000,
        final_balance=10125,
        max_drawdown=0.03,
    )

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "STABLE_OBSERVATION"
    assert evaluation["reasons"] == []

    assert evaluation["account"]["total_pnl"] == 125
    assert evaluation["account"]["return_pct"] == 1.25
    assert evaluation["account"]["max_drawdown"] == 0.03

    print("PASS: stable observation")


def test_drawdown_review():
    evaluator = PaperSessionEvaluator()

    trades = [
        build_trade(30),
        build_trade(-10),
        build_trade(25),
        build_trade(-5),
        build_trade(20),
        build_trade(-5),
        build_trade(15),
        build_trade(-5),
        build_trade(10),
        build_trade(5),
    ]

    report = build_report(
        trades,
        initial_balance=10000,
        final_balance=10080,
        max_drawdown=0.11,
    )

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "REVIEW"

    assert (
        "Maximum drawdown exceeded 10%."
        in evaluation["reasons"]
    )

    assert evaluation["account"]["max_drawdown"] == 0.11

    print("PASS: drawdown review")


def test_report_without_trades():
    evaluator = PaperSessionEvaluator()

    report = {
        "strategy_name": "EMPTY_TEST",
        "mode": "PAPER",
        "live_trading": False,
        "account": {
            "initial_balance": 10000,
            "final_balance": 10000,
        },
        "performance": {
            "pnl": 0,
            "max_drawdown": 0,
        },
        "trades": [],
    }

    evaluation = evaluator.evaluate(report)

    assert evaluation["status"] == "INSUFFICIENT_DATA"
    assert evaluation["trades"]["total_trades"] == 0
    assert evaluation["account"]["total_pnl"] == 0

    print("PASS: empty paper report")


def main():
    print()
    print("=" * 70)
    print("PAPER SESSION EVALUATION TEST")
    print("=" * 70)

    test_basic_statistics()
    test_losing_streak()
    test_review_status_from_losing_streak()
    test_negative_pnl_review()
    test_profit_factor_review()
    test_direction_analysis()
    test_regime_analysis()
    test_recurring_patterns()
    test_stable_observation()
    test_drawdown_review()
    test_report_without_trades()

    print()
    print("=" * 70)
    print("PAPER SESSION EVALUATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()