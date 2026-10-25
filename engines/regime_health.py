import pandas as pd


class RegimeHealthMonitor:
    """
    Measures strategy performance separately for each
    market regime.
    """

    def __init__(
        self,
        minimum_trades=3,
        review_profit_factor=1.0,
        pause_profit_factor=0.80,
        review_win_rate=0.40,
        pause_win_rate=0.30,
    ):
        self.minimum_trades = minimum_trades
        self.review_profit_factor = review_profit_factor
        self.pause_profit_factor = pause_profit_factor
        self.review_win_rate = review_win_rate
        self.pause_win_rate = pause_win_rate

    def calculate_metrics(self, trades):
        if not trades:
            return {
                "trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
            }

        pnl = pd.Series(
            [float(trade["pnl"]) for trade in trades],
            dtype=float,
        )

        winning = pnl[pnl > 0]
        losing = pnl[pnl < 0]

        gross_profit = winning.sum()
        gross_loss = abs(losing.sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        win_rate = (pnl > 0).mean()

        return {
            "trades": len(trades),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "total_pnl": float(pnl.sum()),
        }

    def evaluate_regime(self, trades):
        metrics = self.calculate_metrics(trades)

        if metrics["trades"] < self.minimum_trades:
            return {
                "status": "INSUFFICIENT_DATA",
                "metrics": metrics,
                "reasons": [
                    f"Only {metrics['trades']} trades; "
                    f"{self.minimum_trades} required."
                ],
            }

        status = "ACTIVE"
        reasons = []

        if metrics["profit_factor"] < self.pause_profit_factor:
            status = "PAUSED"
            reasons.append(
                "Profit factor is below the pause threshold."
            )

        if metrics["win_rate"] < self.pause_win_rate:
            status = "PAUSED"
            reasons.append(
                "Win rate is below the pause threshold."
            )

        if status != "PAUSED":

            if metrics["profit_factor"] < self.review_profit_factor:
                status = "REVIEW"
                reasons.append(
                    "Profit factor is below the review threshold."
                )

            if metrics["win_rate"] < self.review_win_rate:
                status = "REVIEW"
                reasons.append(
                    "Win rate is below the review threshold."
                )

        if not reasons:
            reasons.append(
                "Performance is within regime-health thresholds."
            )

        return {
            "status": status,
            "metrics": metrics,
            "reasons": reasons,
        }

    def evaluate_all(self, trades):
        """
        Group trades by market regime and evaluate
        each regime independently.
        """

        regimes = {}

        for trade in trades:
            regime = trade.get(
                "trend_regime",
                "UNKNOWN",
            )

            if regime not in regimes:
                regimes[regime] = []

            regimes[regime].append(trade)

        results = {}

        for regime, regime_trades in regimes.items():
            results[regime] = self.evaluate_regime(
                regime_trades
            )

        return results