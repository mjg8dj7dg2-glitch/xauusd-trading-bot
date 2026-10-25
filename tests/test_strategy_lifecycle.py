from engines.strategy_lifecycle import StrategyLifecycleEngine


def make_robust_result():
    return {
        "validation_trades": 85,
        "windows_with_trades": 4,
        "average_window_profit_factor": 1.1558,
        "positive_window_ratio": 0.75,
        "maximum_window_drawdown": 0.0377,
    }


def make_insufficient_result():
    return {
        "validation_trades": 10,
        "windows_with_trades": 2,
        "average_window_profit_factor": 1.10,
        "positive_window_ratio": 0.25,
        "maximum_window_drawdown": 0.05,
    }


def test_insufficient_validation():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_insufficient_result(),
        paper_trading_complete=False,
        paper_trading_healthy=False,
    )

    assert result["state"] == "VALIDATION"

    print("PASS: insufficient validation -> VALIDATION")


def test_robust_validation_without_paper():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_robust_result(),
        paper_trading_complete=False,
        paper_trading_healthy=False,
    )

    assert result["state"] == "PAPER_TEST"

    print("PASS: robust validation without paper -> PAPER_TEST")


def test_healthy_paper():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_robust_result(),
        paper_trading_complete=True,
        paper_trading_healthy=True,
    )

    assert result["state"] == "ACTIVE"

    print("PASS: healthy paper trading -> ACTIVE")


def test_unhealthy_paper():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_robust_result(),
        paper_trading_complete=True,
        paper_trading_healthy=False,
    )

    assert result["state"] == "REVIEW"

    print("PASS: unhealthy paper trading -> REVIEW")


def test_active_review():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_robust_result(),
        paper_trading_complete=True,
        paper_trading_healthy=True,
        currently_active=True,
        health_status="REVIEW",
    )

    assert result["state"] == "REVIEW"

    print("PASS: active + health REVIEW -> REVIEW")


def test_active_paused():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_robust_result(),
        paper_trading_complete=True,
        paper_trading_healthy=True,
        currently_active=True,
        health_status="PAUSED",
    )

    assert result["state"] == "PAUSED"

    print("PASS: active + health PAUSED -> PAUSED")


def test_active_without_warning():
    engine = StrategyLifecycleEngine()

    result = engine.determine_state(
        robustness_result=make_robust_result(),
        paper_trading_complete=True,
        paper_trading_healthy=True,
        currently_active=True,
        health_status=None,
    )

    assert result["state"] == "ACTIVE"

    print("PASS: active without health warning -> ACTIVE")


def test_evaluate_all():
    engine = StrategyLifecycleEngine()

    robustness_report = {
        "variants": {
            "V1_BASELINE": make_robust_result(),
            "V5_V2_PLUS_V3": make_robust_result(),
        }
    }

    result = engine.evaluate_all(
        robustness_report=robustness_report,
        paper_states={},
        active_strategies={},
        health_states={},
    )

    assert result["status"] == "COMPLETE"

    assert "V1_BASELINE" in result["strategies"]
    assert "V5_V2_PLUS_V3" in result["strategies"]

    assert (
        result["strategies"]["V1_BASELINE"]["state"]
        == "PAPER_TEST"
    )

    assert (
        result["strategies"]["V5_V2_PLUS_V3"]["state"]
        == "PAPER_TEST"
    )

    print(
        "PASS: evaluate_all -> "
        "V1 and V5 both PAPER_TEST"
    )


def test_evaluate_all_with_paper():
    engine = StrategyLifecycleEngine()

    robustness_report = {
        "variants": {
            "V5_V2_PLUS_V3": make_robust_result(),
        }
    }

    paper_states = {
        "V5_V2_PLUS_V3": {
            "complete": True,
            "healthy": True,
        }
    }

    result = engine.evaluate_all(
        robustness_report=robustness_report,
        paper_states=paper_states,
    )

    assert result["status"] == "COMPLETE"

    assert (
        result["strategies"]["V5_V2_PLUS_V3"]["state"]
        == "ACTIVE"
    )

    print(
        "PASS: completed healthy paper trading "
        "-> ACTIVE"
    )


def main():
    print("STRATEGY LIFECYCLE TEST")
    print("=======================")

    test_insufficient_validation()
    test_robust_validation_without_paper()
    test_healthy_paper()
    test_unhealthy_paper()
    test_active_review()
    test_active_paused()
    test_active_without_warning()
    test_evaluate_all()
    test_evaluate_all_with_paper()

    print()
    print("STRATEGY LIFECYCLE TEST PASSED")


if __name__ == "__main__":
    main()