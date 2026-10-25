import pandas as pd


class StrategyHealthMonitor:

    def __init__(
        self,
        minimum_trades=10,
        review_profit_factor=1.0,
        pause_profit_factor=0.80,
        review_win_rate_drop=0.10,
        pause_win_rate_drop=0.20,
        review_drawdown=0.10,
        pause_drawdown=0.15,
        starting_balance=10000.0,
    ):
        self.minimum_trades = minimum_trades
        self.review_profit_factor = review_profit_factor
        self.pause_profit_factor = pause_profit_factor
        self.review_win_rate_drop = review_win_rate_drop
        self.pause_win_rate_drop = pause_win_rate_drop
        self.review_drawdown = review_drawdown
        self.pause_drawdown = pause_drawdown
        self.starting_balance = starting_balance

    def calculate_metrics(self, trades):
        if not trades:
            return {
                "trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
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

        # Build actual account equity.
        equity = self.starting_balance + pnl.cumsum()

        running_peak = equity.cummax()

        drawdown = (
            running_peak - equity
        ) / running_peak

        max_drawdown = drawdown.max()

        return {
            "trades": len(trades),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "total_pnl": float(pnl.sum()),
            "max_drawdown": float(max_drawdown),
        }

    def evaluate(
        self,
        historical_trades,
        recent_trades,
    ):

        historical = self.calculate_metrics(
            historical_trades
        )

        recent = self.calculate_metrics(
            recent_trades
        )

        reasons = []

        if recent["trades"] < self.minimum_trades:
            return {
                "status": "INSUFFICIENT_DATA",
                "historical": historical,
                "recent": recent,
                "win_rate_change": None,
                "profit_factor_change": None,
                "reasons": [
                    f"Only {recent['trades']} recent trades; "
                    f"{self.minimum_trades} required."
                ],
            }

        win_rate_change = (
            recent["win_rate"]
            - historical["win_rate"]
        )

        if historical["profit_factor"] == float("inf"):
            profit_factor_change = None
        else:
            profit_factor_change = (
                recent["profit_factor"]
                - historical["profit_factor"]
            )

        status = "ACTIVE"

        # Severe deterioration.
        if recent["max_drawdown"] >= self.pause_drawdown:
            status = "PAUSED"
            reasons.append(
                "Recent drawdown exceeded the pause threshold."
            )

        if recent["profit_factor"] < self.pause_profit_factor:
            status = "PAUSED"
            reasons.append(
                "Recent profit factor is below the pause threshold."
            )

        if win_rate_change <= -self.pause_win_rate_drop:
            status = "PAUSED"
            reasons.append(
                "Recent win rate dropped significantly."
            )

        # Moderate deterioration.
        if status != "PAUSED":

            if recent["profit_factor"] < self.review_profit_factor:
                status = "REVIEW"
                reasons.append(
                    "Recent profit factor is below "
                    "the review threshold."
                )

            if win_rate_change <= -self.review_win_rate_drop:
                status = "REVIEW"
                reasons.append(
                    "Recent win rate has deteriorated."
                )

            if recent["max_drawdown"] >= self.review_drawdown:
                status = "REVIEW"
                reasons.append(
                    "Recent drawdown exceeded "
                    "the review threshold."
                )

        if not reasons:
            reasons.append(
                "Recent performance remains within "
                "health thresholds."
            )

        return {
            "status": status,
            "historical": historical,
            "recent": recent,
            "win_rate_change": win_rate_change,
            "profit_factor_change": profit_factor_change,
            "reasons": reasons,
        }