from __future__ import annotations

from collections import defaultdict
from math import isfinite


class PaperSessionEvaluator:
    """
    Evaluates a completed paper-trading report.

    This module is analysis-only:
    - It does not place trades.
    - It does not modify signals.
    - It does not change strategy rules.
    - It does not automatically pause or alter a strategy.

    It produces a structured evaluation that can later feed
    strategy health and the Streamlit dashboard.
    """

    def __init__(
        self,
        losing_streak_review_threshold: int = 5,
        minimum_trades_for_regime_analysis: int = 5,
    ):
        self.losing_streak_review_threshold = int(
            losing_streak_review_threshold
        )

        self.minimum_trades_for_regime_analysis = int(
            minimum_trades_for_regime_analysis
        )

    # ------------------------------------------------------------------
    # Basic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _number(value, default=0.0):
        try:
            result = float(value)

            if isfinite(result):
                return result

        except (TypeError, ValueError):
            pass

        return float(default)

    @staticmethod
    def _trade_pnl(trade):
        if not isinstance(trade, dict):
            return 0.0

        for key in (
            "pnl",
            "profit",
            "profit_loss",
            "realized_pnl",
        ):
            if key in trade:
                return PaperSessionEvaluator._number(
                    trade.get(key)
                )

        return 0.0

    @staticmethod
    def _trade_direction(trade):
        if not isinstance(trade, dict):
            return "UNKNOWN"

        value = (
            trade.get("direction")
            or trade.get("side")
            or trade.get("signal")
            or "UNKNOWN"
        )

        return str(value).upper()

    @staticmethod
    def _trade_regime(trade, keys):
        if not isinstance(trade, dict):
            return "UNKNOWN"

        for key in keys:
            value = trade.get(key)

            if value not in (None, ""):
                return str(value)

        return "UNKNOWN"

    # ------------------------------------------------------------------
    # Drawdown
    # ------------------------------------------------------------------

    def _calculate_max_drawdown(self, equity_curve):
        """
        Calculates maximum percentage drawdown from an equity curve.

        Supports:
            - numbers
            - dictionaries containing equity
            - dictionaries containing balance

        Returns:
            Decimal percentage.

        Example:
            0.0568 = 5.68%
        """

        if equity_curve is None:
            return 0.0

        try:
            points = list(equity_curve)
        except TypeError:
            return 0.0

        peak = None
        maximum_drawdown = 0.0

        for point in points:
            if isinstance(point, dict):
                value = point.get("equity")

                if value is None:
                    value = point.get("balance")

            else:
                value = point

            value = self._number(
                value,
                default=float("nan"),
            )

            if not isfinite(value):
                continue

            if value <= 0:
                continue

            if peak is None or value > peak:
                peak = value
                continue

            if peak <= 0:
                continue

            drawdown = (
                peak - value
            ) / peak

            if drawdown > maximum_drawdown:
                maximum_drawdown = drawdown

        return maximum_drawdown

    def _resolve_max_drawdown(
        self,
        report,
        account,
        performance,
    ):
        """
        Resolves maximum drawdown.

        IMPORTANT:
        A persisted/in-memory equity curve is authoritative when
        available. This prevents a stale placeholder such as
        max_drawdown=0.0 from hiding the actual drawdown.

        Explicit drawdown fields are used only when no usable
        equity curve is available.
        """

        equity_curve = report.get(
            "equity_curve",
            [],
        )

        try:
            points = list(equity_curve)
        except TypeError:
            points = []

        if points:
            calculated_drawdown = (
                self._calculate_max_drawdown(points)
            )

            return calculated_drawdown

        explicit_candidates = (
            performance.get("max_drawdown"),
            account.get("max_drawdown"),
            report.get("max_drawdown"),
        )

        for value in explicit_candidates:
            if value is not None:
                return self._number(value)

        return 0.0

    # ------------------------------------------------------------------
    # Trade statistics
    # ------------------------------------------------------------------

    def _trade_statistics(self, trades):
        pnl_values = [
            self._trade_pnl(trade)
            for trade in trades
        ]

        wins = [
            pnl for pnl in pnl_values
            if pnl > 0
        ]

        losses = [
            pnl for pnl in pnl_values
            if pnl < 0
        ]

        total_pnl = sum(pnl_values)
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))

        if gross_loss > 0:
            profit_factor = (
                gross_profit / gross_loss
            )
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        total_trades = len(pnl_values)

        win_rate = (
            len(wins) / total_trades
            if total_trades
            else 0.0
        )

        average_trade = (
            total_pnl / total_trades
            if total_trades
            else 0.0
        )

        average_win = (
            sum(wins) / len(wins)
            if wins
            else 0.0
        )

        average_loss = (
            sum(losses) / len(losses)
            if losses
            else 0.0
        )

        return {
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "average_trade": average_trade,
            "average_win": average_win,
            "average_loss": average_loss,
        }

    # ------------------------------------------------------------------
    # Losing streak
    # ------------------------------------------------------------------

    def _losing_streak(self, trades):
        current = 0
        maximum = 0

        for trade in trades:
            pnl = self._trade_pnl(trade)

            if pnl < 0:
                current += 1
                maximum = max(maximum, current)
            else:
                current = 0

        return maximum

    # ------------------------------------------------------------------
    # Direction analysis
    # ------------------------------------------------------------------

    def _group_analysis(self, trades, key_function):
        groups = defaultdict(list)

        for trade in trades:
            key = key_function(trade)
            groups[key].append(trade)

        result = {}

        for key, group in groups.items():
            statistics = self._trade_statistics(group)

            result[str(key)] = statistics

        return result

    # ------------------------------------------------------------------
    # Regime analysis
    # ------------------------------------------------------------------

    def _regime_analysis(self, trades):
        trend = self._group_analysis(
            trades,
            lambda trade: self._trade_regime(
                trade,
                (
                    "trend_regime",
                    "trend",
                    "market_trend",
                ),
            ),
        )

        volatility = self._group_analysis(
            trades,
            lambda trade: self._trade_regime(
                trade,
                (
                    "volatility_regime",
                    "volatility",
                    "market_volatility",
                ),
            ),
        )

        return {
            "trend": trend,
            "volatility": volatility,
        }

    # ------------------------------------------------------------------
    # Worst recurring conditions
    # ------------------------------------------------------------------

    def _pattern_analysis(self, trades):
        """
        Looks for simple recurring categorical combinations.

        This is deliberately descriptive. It does not automatically
        convert a pattern into a strategy rule.
        """

        patterns = defaultdict(list)

        for trade in trades:
            if not isinstance(trade, dict):
                continue

            direction = self._trade_direction(trade)

            trend = self._trade_regime(
                trade,
                (
                    "trend_regime",
                    "trend",
                    "market_trend",
                ),
            )

            volatility = self._trade_regime(
                trade,
                (
                    "volatility_regime",
                    "volatility",
                    "market_volatility",
                ),
            )

            key = (
                direction,
                trend,
                volatility,
            )

            patterns[key].append(trade)

        results = []

        for key, group in patterns.items():
            if len(group) < self.minimum_trades_for_regime_analysis:
                continue

            statistics = self._trade_statistics(group)

            results.append(
                {
                    "direction": key[0],
                    "trend_regime": key[1],
                    "volatility_regime": key[2],
                    **statistics,
                }
            )

        results.sort(
            key=lambda item: item["total_pnl"]
        )

        return {
            "worst": results[:10],
            "best": list(
                reversed(results[-10:])
            ),
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, report):
        if not isinstance(report, dict):
            raise TypeError(
                "PaperSessionEvaluator expects a report dictionary."
            )

        trades = report.get("trades", [])

        if trades is None:
            trades = []

        if not isinstance(trades, list):
            try:
                trades = list(trades)
            except TypeError as exc:
                raise TypeError(
                    "Report trades must be a list or iterable."
                ) from exc

        account = report.get("account", {})
        performance = report.get("performance", {})
        risk = report.get("risk", {})

        if not isinstance(account, dict):
            account = {}

        if not isinstance(performance, dict):
            performance = {}

        if not isinstance(risk, dict):
            risk = {}

        statistics = self._trade_statistics(trades)

        initial_balance = self._number(
            account.get(
                "initial_balance",
                performance.get(
                    "initial_balance",
                    0.0,
                ),
            )
        )

        final_balance = self._number(
            account.get(
                "final_balance",
                performance.get(
                    "final_balance",
                    initial_balance,
                ),
            )
        )

        total_pnl = final_balance - initial_balance

        if not trades:
            total_pnl = self._number(
                performance.get(
                    "pnl",
                    total_pnl,
                )
            )

        losing_streak = self._losing_streak(
            trades
        )

        max_drawdown = self._resolve_max_drawdown(
            report=report,
            account=account,
            performance=performance,
        )

        evaluation_status = "INSUFFICIENT_DATA"
        reasons = []

        if len(trades) >= 10:
            evaluation_status = "OBSERVATION"

            if total_pnl < 0:
                reasons.append(
                    "Paper-session P&L is negative."
                )

            if losing_streak >= self.losing_streak_review_threshold:
                reasons.append(
                    "A prolonged losing streak was observed."
                )

            if max_drawdown > 0.10:
                reasons.append(
                    "Maximum drawdown exceeded 10%."
                )

            if (
                statistics["profit_factor"] > 0
                and statistics["profit_factor"] < 1.0
            ):
                reasons.append(
                    "Profit factor is below 1.0."
                )

            if not reasons:
                evaluation_status = "STABLE_OBSERVATION"
            else:
                evaluation_status = "REVIEW"

        return {
            "status": evaluation_status,
            "strategy_name": report.get(
                "strategy_name",
                "UNKNOWN",
            ),
            "mode": report.get(
                "mode",
                "PAPER",
            ),
            "live_trading": bool(
                report.get(
                    "live_trading",
                    False,
                )
            ),
            "account": {
                "initial_balance": initial_balance,
                "final_balance": final_balance,
                "total_pnl": total_pnl,
                "return_pct": (
                    total_pnl / initial_balance * 100.0
                    if initial_balance > 0
                    else 0.0
                ),
                "max_drawdown": max_drawdown,
            },
            "trades": statistics,
            "losing_streak": {
                "maximum": losing_streak,
                "review_threshold": (
                    self.losing_streak_review_threshold
                ),
            },
            "direction": self._group_analysis(
                trades,
                self._trade_direction,
            ),
            "regime": self._regime_analysis(
                trades
            ),
            "patterns": self._pattern_analysis(
                trades
            ),
            "risk": risk,
            "reasons": reasons,
        }

    # ------------------------------------------------------------------
    # Human-readable report
    # ------------------------------------------------------------------

    def print_report(self, evaluation):
        print()
        print("=" * 80)
        print("PAPER SESSION EVALUATION")
        print("=" * 80)

        print(
            f"Status:             {evaluation['status']}"
        )

        account = evaluation["account"]

        print(
            f"Initial balance:    {account['initial_balance']:,.2f}"
        )

        print(
            f"Final balance:      {account['final_balance']:,.2f}"
        )

        print(
            f"P&L:                {account['total_pnl']:+,.2f}"
        )

        print(
            f"Return:             {account['return_pct']:+.2f}%"
        )

        print(
            f"Max drawdown:       {account['max_drawdown']:.2%}"
        )

        trades = evaluation["trades"]

        print(
            f"Trades:             {trades['total_trades']}"
        )

        print(
            f"Win rate:           {trades['win_rate']:.2%}"
        )

        print(
            f"Profit factor:      {trades['profit_factor']:.4f}"
        )

        print(
            f"Average trade:      {trades['average_trade']:+,.2f}"
        )

        print(
            f"Maximum losing streak: "
            f"{evaluation['losing_streak']['maximum']}"
        )

        print()

        if evaluation["reasons"]:
            print("REVIEW REASONS")

            for reason in evaluation["reasons"]:
                print(f"  - {reason}")

        else:
            print(
                "No immediate evaluation warnings."
            )

        print("=" * 80)


if __name__ == "__main__":
    print(
        "PaperSessionEvaluator module loaded."
    )