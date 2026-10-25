import pandas as pd

from engines.paper_trading import (
    PaperTradingEngine,
)
from engines.strategy_experiment import (
    get_standard_variants,
)


def make_test_data():
    timestamps = pd.date_range(
        "2026-01-01",
        periods=12,
        freq="5min",
        tz="UTC",
    )

    rows = []

    prices = [
        100.0,
        100.0,
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        103.0,
        102.0,
        101.0,
        100.0,
        99.0,
    ]

    for index, price in enumerate(prices):
        rows.append(
            {
                "timestamp": timestamps[index],
                "open": price,
                "high": price + 0.25,
                "low": price - 0.25,
                "close": price,
                "volume": 1000,
                "signal": (
                    "LONG"
                    if index == 2
                    else "NO_SIGNAL"
                ),
                "atr": 1.0,
                "rsi": 55.0,
                "ema": 101.0,
                "sma": 100.0,
                "trend_regime": "TRENDING_UP",
                "volatility_regime": "LOW_VOLATILITY",
                "signal_strength": 1.0,
                "signal_reason": "Test signal",
            }
        )

    return pd.DataFrame(rows)


def test_paper_engine_basic():
    data = make_test_data()

    engine = PaperTradingEngine(
        initial_balance=10_000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=1.0,
        take_profit_ratio=1.0,
    )

    report = engine.run(
        analyzed_data=data,
        strategy_name="TEST_STRATEGY",
    )

    assert report["status"] == "COMPLETE"
    assert report["mode"] == "PAPER"
    assert report["live_trading"] is False
    assert report["strategy_name"] == "TEST_STRATEGY"

    assert report["data"]["rows"] == 12
    assert report["data"]["strategy_signal_count"] == 1

    assert report["performance"]["trades"] == 1
    assert report["performance"]["wins"] == 1
    assert report["performance"]["losses"] == 0

    assert (
        report["account"]["final_balance"]
        > report["account"]["initial_balance"]
    )

    assert len(report["trades"]) == 1
    assert report["trades"][0]["direction"] == "LONG"

    print(
        "PASS: basic paper simulation"
    )


def test_strategy_transform_blocks_signal():
    data = make_test_data()

    def block_all_signals(df):
        result = df.copy()

        mask = result["signal"].isin(
            ["LONG", "SHORT"]
        )

        result.loc[
            mask,
            "signal"
        ] = "NO_SIGNAL"

        return result

    engine = PaperTradingEngine()

    report = engine.run(
        analyzed_data=data,
        strategy_name="BLOCKED_TEST",
        strategy_transform=block_all_signals,
    )

    assert report["status"] == "COMPLETE"

    assert (
        report["data"]["original_signal_count"]
        == 1
    )

    assert (
        report["data"]["strategy_signal_count"]
        == 0
    )

    assert (
        report["data"]["strategy_blocked_signals"]
        == 1
    )

    assert report["performance"]["trades"] == 0

    print(
        "PASS: strategy transform blocks signal"
    )


def test_v5_variant_is_accepted():
    data = make_test_data()

    variants = dict(
        get_standard_variants()
    )

    assert "V5_V2_PLUS_V3" in variants

    engine = PaperTradingEngine()

    report = engine.run(
        analyzed_data=data,
        strategy_name="V5_V2_PLUS_V3",
        strategy_transform=variants[
            "V5_V2_PLUS_V3"
        ],
    )

    assert report["status"] == "COMPLETE"
    assert (
        report["strategy_name"]
        == "V5_V2_PLUS_V3"
    )
    assert report["live_trading"] is False

    print(
        "PASS: V5 strategy variant accepted"
    )


def main():
    print("PAPER TRADING TEST")
    print("==================")

    test_paper_engine_basic()
    test_strategy_transform_blocks_signal()
    test_v5_variant_is_accepted()

    print()
    print("PAPER TRADING TEST PASSED")


if __name__ == "__main__":
    main()