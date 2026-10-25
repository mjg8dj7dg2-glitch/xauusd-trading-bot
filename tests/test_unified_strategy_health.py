from engines.strategy_evaluation import StrategyEvaluationEngine


def robustness(
    trades=40,
    windows=4,
    pf=1.30,
    positive_ratio=0.75,
    pnl=500.0,
    drawdown=0.05,
):
    return {
        "status": "ROBUST",
        "validation_trades": trades,
        "windows_with_trades": windows,
        "average_window_profit_factor": pf,
        "positive_window_ratio": positive_ratio,
        "total_validation_pnl": pnl,
        "maximum_window_drawdown": drawdown,
    }


def main():
    print()
    print("=" * 80)
    print("UNIFIED STRATEGY HEALTH TEST")
    print("=" * 80)

    engine = StrategyEvaluationEngine()

    # ------------------------------------------------------------
    # ACTIVE
    # ------------------------------------------------------------

    active = engine.evaluate_variant(
        variant_name="TEST_ACTIVE",
        robustness_result=robustness(),
        paper_state={
            "complete": True,
            "healthy": True,
            "state": "STABLE",
            "trades": 20,
        },
        currently_active=False,
        health_status="ACTIVE",
        regime_report={
            "TRENDING_UP": {
                "status": "ACTIVE",
            },
            "TRENDING_DOWN": {
                "status": "ACTIVE",
            },
        },
        strategy_health_report={
            "status": "ACTIVE",
        },
        paper_evaluation={
            "status": "STABLE_OBSERVATION",
        },
    )

    assert active["overall"]["status"] == "ACTIVE"

    print("PASS: healthy strategy classified ACTIVE")

    # ------------------------------------------------------------
    # REVIEW FROM PAPER EVALUATION
    # ------------------------------------------------------------

    review = engine.evaluate_variant(
        variant_name="TEST_REVIEW",
        robustness_result=robustness(),
        paper_state={
            "complete": True,
            "healthy": False,
            "state": "REVIEW",
            "trades": 20,
        },
        health_status="ACTIVE",
        regime_report={
            "TRENDING_UP": {
                "status": "ACTIVE",
            },
        },
        paper_evaluation={
            "status": "REVIEW",
        },
    )

    assert review["overall"]["status"] == "REVIEW"

    print("PASS: paper review condition classified REVIEW")

    # ------------------------------------------------------------
    # PAUSED FROM STRATEGY HEALTH
    # ------------------------------------------------------------

    paused = engine.evaluate_variant(
        variant_name="TEST_PAUSED",
        robustness_result=robustness(),
        paper_state={
            "complete": True,
            "healthy": True,
            "state": "STABLE",
            "trades": 20,
        },
        health_status="PAUSED",
        regime_report={
            "TRENDING_UP": {
                "status": "ACTIVE",
            },
        },
        paper_evaluation={
            "status": "STABLE_OBSERVATION",
        },
    )

    assert paused["overall"]["status"] == "PAUSED"

    print("PASS: paused strategy health classified PAUSED")

    # ------------------------------------------------------------
    # PAUSED REGIME
    # ------------------------------------------------------------

    regime_paused = engine.evaluate_variant(
        variant_name="TEST_REGIME_PAUSED",
        robustness_result=robustness(),
        paper_state={
            "complete": True,
            "healthy": True,
            "state": "STABLE",
            "trades": 20,
        },
        health_status="ACTIVE",
        regime_report={
            "TRENDING_UP": {
                "status": "PAUSED",
            },
        },
        paper_evaluation={
            "status": "STABLE_OBSERVATION",
        },
    )

    assert (
        regime_paused["overall"]["status"]
        == "PAUSED"
    )

    print("PASS: paused regime classified PAUSED")

    # ------------------------------------------------------------
    # VALIDATION / INSUFFICIENT DATA
    # ------------------------------------------------------------

    insufficient = engine.evaluate_variant(
        variant_name="TEST_INSUFFICIENT",
        robustness_result=robustness(
            trades=10,
            windows=2,
            pf=0.90,
            positive_ratio=0.50,
        ),
        paper_state={
            "complete": False,
            "healthy": False,
            "state": "NOT_STARTED",
            "trades": 0,
        },
        health_status="INSUFFICIENT_DATA",
    )

    assert (
        insufficient["overall"]["status"]
        == "INSUFFICIENT_DATA"
    )

    print(
        "PASS: insufficient evidence classified "
        "INSUFFICIENT_DATA"
    )

    # ------------------------------------------------------------
    # EVALUATE ALL + SUMMARY
    # ------------------------------------------------------------

    report = engine.evaluate_all(
        robustness_report={
            "variants": {
                "ACTIVE_TEST": robustness(),
                "REVIEW_TEST": robustness(),
            }
        },
        paper_states={
            "ACTIVE_TEST": {
                "complete": True,
                "healthy": True,
                "state": "STABLE",
                "trades": 20,
            },
            "REVIEW_TEST": {
                "complete": True,
                "healthy": False,
                "state": "REVIEW",
                "trades": 20,
            },
        },
        health_states={
            "ACTIVE_TEST": "ACTIVE",
            "REVIEW_TEST": "REVIEW",
        },
        regime_reports={
            "ACTIVE_TEST": {
                "TRENDING_UP": {
                    "status": "ACTIVE",
                }
            },
            "REVIEW_TEST": {
                "TRENDING_DOWN": {
                    "status": "REVIEW",
                }
            },
        },
        paper_evaluations={
            "ACTIVE_TEST": {
                "status": "STABLE_OBSERVATION",
            },
            "REVIEW_TEST": {
                "status": "REVIEW",
            },
        },
    )

    assert report["status"] == "COMPLETE"
    assert report["strategy_count"] == 2
    assert report["status_counts"]["ACTIVE"] == 1
    assert report["status_counts"]["REVIEW"] == 1

    print(
        "PASS: multi-strategy unified report generated"
    )

    summary = (
        engine.build_dashboard_summary(report)
    )

    assert summary["strategy_count"] == 2
    assert summary["active"] == 1
    assert summary["review"] == 1

    print(
        "PASS: dashboard summary generated"
    )

    engine.print_report(report)

    print()
    print("=" * 80)
    print("UNIFIED STRATEGY HEALTH TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()