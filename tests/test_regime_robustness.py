import pandas as pd

from engines.regime_robustness import RegimeRobustnessAnalyzer


def build_test_trades():
    return pd.DataFrame(
        [
            {
                "pnl": 100.0,
                "direction": "LONG",
                "trend_regime": "TRENDING_UP",
                "volatility_regime": "LOW_VOLATILITY",
            },
            {
                "pnl": 80.0,
                "direction": "LONG",
                "trend_regime": "TRENDING_UP",
                "volatility_regime": "LOW_VOLATILITY",
            },
            {
                "pnl": -50.0,
                "direction": "SHORT",
                "trend_regime": "TRENDING_DOWN",
                "volatility_regime": "LOW_VOLATILITY",
            },
            {
                "pnl": -70.0,
                "direction": "SHORT",
                "trend_regime": "TRENDING_DOWN",
                "volatility_regime": "LOW_VOLATILITY",
            },
            {
                "pnl": -40.0,
                "direction": "SHORT",
                "trend_regime": "RANGING",
                "volatility_regime": "LOW_VOLATILITY",
            },
            {
                "pnl": 20.0,
                "direction": "LONG",
                "trend_regime": "RANGING",
                "volatility_regime": "NORMAL_VOLATILITY",
            },
        ]
    )


def test_basic_regime_analysis():
    trades = build_test_trades()

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=2
    )

    trend = analyzer.analyze_trend_regime(trades)

    assert not trend.empty

    trending_up = trend[
        trend["trend_regime"] == "TRENDING_UP"
    ].iloc[0]

    assert trending_up["trades"] == 2
    assert trending_up["wins"] == 2
    assert trending_up["win_rate"] == 1.0
    assert trending_up["total_pnl"] == 180.0
    assert trending_up["profit_factor"] == float("inf")


def test_direction_analysis():
    trades = build_test_trades()

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=2
    )

    direction = analyzer.analyze_direction(trades)

    long_row = direction[
        direction["direction"] == "LONG"
    ].iloc[0]

    short_row = direction[
        direction["direction"] == "SHORT"
    ].iloc[0]

    # LONG trades:
    # +100, +80, +20
    assert long_row["trades"] == 3
    assert long_row["wins"] == 3
    assert long_row["losses"] == 0
    assert long_row["total_pnl"] == 200.0

    # SHORT trades:
    # -50, -70, -40
    assert short_row["trades"] == 3
    assert short_row["wins"] == 0
    assert short_row["losses"] == 3
    assert short_row["total_pnl"] == -160.0


def test_combined_regime_analysis():
    trades = build_test_trades()

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=1
    )

    result = analyzer.analyze_trend_and_volatility(
        trades
    )

    assert not result.empty

    assert "trend_regime" in result.columns
    assert "volatility_regime" in result.columns
    assert "profit_factor" in result.columns


def test_weak_regime_detection():
    trades = build_test_trades()

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=2
    )

    weak = analyzer.find_weak_regimes(trades)

    assert "trend_regime" in weak

    trend_weak = weak["trend_regime"]

    assert not trend_weak.empty

    assert (
        trend_weak["trend_regime"]
        .isin(
            [
                "TRENDING_DOWN",
                "RANGING",
            ]
        )
        .any()
    )


def test_positive_regime_detection():
    trades = build_test_trades()

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=2
    )

    positive = analyzer.find_positive_regimes(trades)

    assert "trend_regime" in positive

    trend_positive = positive["trend_regime"]

    assert not trend_positive.empty

    assert (
        trend_positive["trend_regime"]
        .isin(["TRENDING_UP"])
        .any()
    )


def test_insufficient_data():
    trades = pd.DataFrame(
        [
            {
                "pnl": 100.0,
                "direction": "LONG",
                "trend_regime": "TRENDING_UP",
                "volatility_regime": "LOW_VOLATILITY",
            }
        ]
    )

    analyzer = RegimeRobustnessAnalyzer(
        minimum_trades=5
    )

    result = analyzer.analyze_trend_regime(
        trades
    )

    row = result.iloc[0]

    assert row["trades"] == 1
    assert row["status"] == "INSUFFICIENT_DATA"


if __name__ == "__main__":
    test_basic_regime_analysis()
    test_direction_analysis()
    test_combined_regime_analysis()
    test_weak_regime_detection()
    test_positive_regime_detection()
    test_insufficient_data()

    print()
    print("REGIME ROBUSTNESS TEST PASSED")