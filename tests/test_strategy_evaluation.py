from engines.strategy_evaluation import (
    StrategyEvaluationEngine,
)


def make_robust_result():
    return {
        "status": "ROBUST",
        "validation_trades": 48,
        "windows_with_trades": 4,
        "average_window_profit_factor": 1.9221,
        "positive_window_ratio": 0.75,
        "total_validation_pnl": 847.63,
        "maximum_window_drawdown": 0.0139,
    }


def make_validation_result():
    return {
        "status": "VALIDATION",
        "validation_trades": 10,
        "windows_with_trades": 2,
        "average_window_profit_factor": 0.90,
        "positive_window_ratio": 0.50,
        "total_validation_pnl": -25.0,
        "maximum_window_drawdown": 0.05,
    }


def test_robust_strategy_without_paper():
    engine = StrategyEvaluationEngine()

    report = {
        "variants": {
            "V5_V2_PLUS_V3": make_robust_result(),
        }
    }

    result = engine.evaluate_all(
        robustness_report=report,
    )

    strategy = result["strategies"][
        "V5_V2_PLUS_V3"
    ]

    assert result["status"] == "COMPLETE"
    assert result["strategy_count"] == 1

    assert (
        strategy["robustness"]["status"]
        == "ROBUST"
    )

    assert (
        strategy["lifecycle"]["state"]
        == "PAPER_TEST"
    )

    assert (
        strategy["paper_trading"]["complete"]
        is False
    )

    print(
        "PASS: robust strategy without paper "
        "-> PAPER_TEST"
    )


def test_robust_strategy_with_healthy_paper():
    engine = StrategyEvaluationEngine()

    report = {
        "variants": {
            "V5_V2_PLUS_V3": make_robust_result(),
        }
    }

    paper_states = {
        "V5_V2_PLUS_V3": {
            "complete": True,
            "healthy": True,
            "state": "PAPER_TEST",
            "trades": 25,
        }
    }

    result = engine.evaluate_all(
        robustness_report=report,
        paper_states=paper_states,
    )

    strategy = result["strategies"][
        "V5_V2_PLUS_V3"
    ]

    assert (
        strategy["lifecycle"]["state"]
        == "ACTIVE"
    )

    assert (
        strategy["paper_trading"]["complete"]
        is True
    )

    assert (
        strategy["paper_trading"]["healthy"]
        is True
    )

    assert (
        strategy["paper_trading"]["trades"]
        == 25
    )

    print(
        "PASS: robust + healthy paper "
        "-> ACTIVE"
    )


def test_active_strategy_health_warning():
    engine = StrategyEvaluationEngine()

    report = {
        "variants": {
            "V5_V2_PLUS_V3": make_robust_result(),
        }
    }

    result = engine.evaluate_all(
        robustness_report=report,
        paper_states={
            "V5_V2_PLUS_V3": {
                "complete": True,
                "healthy": True,
            }
        },
        active_strategies={
            "V5_V2_PLUS_V3": True,
        },
        health_states={
            "V5_V2_PLUS_V3": "REVIEW",
        },
    )

    strategy = result["strategies"][
        "V5_V2_PLUS_V3"
    ]

    assert (
        strategy["lifecycle"]["state"]
        == "REVIEW"
    )

    print(
        "PASS: active strategy + REVIEW health "
        "-> REVIEW"
    )


def test_insufficient_strategy():
    engine = StrategyEvaluationEngine()

    report = {
        "variants": {
            "V1_BASELINE": make_validation_result(),
        }
    }

    result = engine.evaluate_all(
        robustness_report=report,
    )

    strategy = result["strategies"][
        "V1_BASELINE"
    ]

    assert (
        strategy["lifecycle"]["state"]
        == "VALIDATION"
    )

    print(
        "PASS: insufficient evidence "
        "-> VALIDATION"
    )


def test_optional_analysis_is_preserved():
    engine = StrategyEvaluationEngine()

    report = {
        "variants": {
            "V5_V2_PLUS_V3": make_robust_result(),
        }
    }

    regime_report = {
        "TREND_AND_VOLATILITY": {
            "status": "AVAILABLE"
        }
    }

    health_report = {
        "status": "ACTIVE",
        "recent_trades": 20,
    }

    memory_report = {
        "similar_trades": 5,
        "losing_patterns": 2,
    }

    result = engine.evaluate_all(
        robustness_report=report,
        regime_reports={
            "V5_V2_PLUS_V3": regime_report,
        },
        strategy_health_reports={
            "V5_V2_PLUS_V3": health_report,
        },
        memory_reports={
            "V5_V2_PLUS_V3": memory_report,
        },
    )

    strategy = result["strategies"][
        "V5_V2_PLUS_V3"
    ]

    assert (
        strategy["regime_analysis"]
        == regime_report
    )

    assert (
        strategy["health"]["report"]
        == health_report
    )

    assert (
        strategy["trade_memory"]
        == memory_report
    )

    print(
        "PASS: regime, health and memory "
        "evidence preserved"
    )


def main():
    print("STRATEGY EVALUATION TEST")
    print("========================")

    test_robust_strategy_without_paper()
    test_robust_strategy_with_healthy_paper()
    test_active_strategy_health_warning()
    test_insufficient_strategy()
    test_optional_analysis_is_preserved()

    print()
    print("STRATEGY EVALUATION TEST PASSED")


if __name__ == "__main__":
    main()