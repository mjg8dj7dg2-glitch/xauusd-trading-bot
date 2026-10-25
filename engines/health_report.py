from engines.strategy_health import StrategyHealthMonitor
from engines.regime_health import RegimeHealthMonitor


class HealthReport:
    """
    Combines strategy-level and market-regime-level health checks.
    """

    def __init__(
        self,
        starting_balance=10000.0,
        minimum_recent_trades=5,
        minimum_regime_trades=3,
    ):
        self.strategy_monitor = StrategyHealthMonitor(
            minimum_trades=minimum_recent_trades,
            starting_balance=starting_balance,
        )

        self.regime_monitor = RegimeHealthMonitor(
            minimum_trades=minimum_regime_trades,
        )

    def build_report(
        self,
        historical_trades,
        recent_trades,
        all_trades,
    ):
        strategy_health = self.strategy_monitor.evaluate(
            historical_trades=historical_trades,
            recent_trades=recent_trades,
        )

        regime_health = self.regime_monitor.evaluate_all(
            all_trades
        )

        return {
            "strategy_health": strategy_health,
            "regime_health": regime_health,
        }

    def get_strategy_status(self, report):
        return report["strategy_health"]["status"]

    def get_regime_statuses(self, report):
        statuses = {}

        regime_health = report.get(
            "regime_health",
            {},
        )

        for regime, result in regime_health.items():
            statuses[regime] = result.get(
                "status",
                "UNKNOWN",
            )

        return statuses

    def summarize(self, report):
        strategy = report["strategy_health"]

        regime_health = report.get(
            "regime_health",
            {},
        )

        active_regimes = 0
        review_regimes = 0
        paused_regimes = 0
        insufficient_regimes = 0

        for result in regime_health.values():
            status = result.get(
                "status",
                "UNKNOWN",
            )

            if status == "ACTIVE":
                active_regimes += 1

            elif status == "REVIEW":
                review_regimes += 1

            elif status == "PAUSED":
                paused_regimes += 1

            elif status == "INSUFFICIENT_DATA":
                insufficient_regimes += 1

        return {
            "strategy_status": strategy["status"],
            "strategy_reason_count": len(
                strategy.get("reasons", [])
            ),
            "active_regimes": active_regimes,
            "review_regimes": review_regimes,
            "paused_regimes": paused_regimes,
            "insufficient_regimes": insufficient_regimes,
        }