from __future__ import annotations

from typing import Any, Dict


class PaperTradingMonitor:
    """
    Evaluates the health of a historical paper-trading report.

    This class is analysis-only.

    It does NOT:
        - place trades
        - connect to a broker
        - change strategy rules
        - change risk settings
        - promote a strategy automatically

    Possible statuses:

        INSUFFICIENT_DATA
        HEALTHY
        WARNING
        PAUSED

    The monitor accepts both the compact performance field names:

        trades
        wins
        losses

    and the paper-trading engine field names:

        total_trades
        winning_trades
        losing_trades
    """

    def __init__(
        self,
        minimum_trades: int = 20,
        healthy_profit_factor: float = 1.10,
        warning_profit_factor: float = 1.00,
        healthy_win_rate: float = 0.35,
        warning_win_rate: float = 0.30,
        maximum_drawdown: float = 0.10,
        warning_drawdown: float = 0.07,
        maximum_losing_streak: int = 7,
        maximum_blocked_entry_ratio: float = 0.50,
    ):
        self.minimum_trades = int(
            minimum_trades
        )

        self.healthy_profit_factor = float(
            healthy_profit_factor
        )

        self.warning_profit_factor = float(
            warning_profit_factor
        )

        self.healthy_win_rate = float(
            healthy_win_rate
        )

        self.warning_win_rate = float(
            warning_win_rate
        )

        self.maximum_drawdown = float(
            maximum_drawdown
        )

        self.warning_drawdown = float(
            warning_drawdown
        )

        self.maximum_losing_streak = int(
            maximum_losing_streak
        )

        self.maximum_blocked_entry_ratio = float(
            maximum_blocked_entry_ratio
        )

    @staticmethod
    def _number(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _integer(
        value: Any,
        default: int = 0,
    ) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_first_value(
        data: Dict[str, Any],
        keys,
        default=None,
    ):
        for key in keys:
            if key in data:
                return data[key]

        return default

    @staticmethod
    def _calculate_losing_streak(
        trades,
    ) -> int:
        current_streak = 0
        maximum_streak = 0

        for trade in trades:
            pnl = PaperTradingMonitor._number(
                trade.get("pnl", 0.0)
            )

            if pnl < 0:
                current_streak += 1

                if current_streak > maximum_streak:
                    maximum_streak = current_streak

            else:
                current_streak = 0

        return maximum_streak

    @staticmethod
    def _calculate_current_losing_streak(
        trades,
    ) -> int:
        current_streak = 0

        for trade in reversed(trades):
            pnl = PaperTradingMonitor._number(
                trade.get("pnl", 0.0)
            )

            if pnl < 0:
                current_streak += 1
            else:
                break

        return current_streak

    @staticmethod
    def _calculate_blocked_ratio(
        risk: Dict[str, Any],
    ) -> float:
        blocked = PaperTradingMonitor._integer(
            PaperTradingMonitor._get_first_value(
                risk,
                [
                    "blocked_entries",
                    "blocked",
                ],
                0,
            )
        )

        allowed = PaperTradingMonitor._integer(
            PaperTradingMonitor._get_first_value(
                risk,
                [
                    "allowed_entries",
                    "allowed",
                ],
                0,
            )
        )

        executed = PaperTradingMonitor._integer(
            PaperTradingMonitor._get_first_value(
                risk,
                [
                    "executed_trades",
                    "executed_entries",
                ],
                0,
            )
        )

        total = blocked + allowed

        if total <= 0:
            total = blocked + executed

        if total <= 0:
            return 0.0

        return blocked / total

    @staticmethod
    def _extract_regime_warnings(
        regime_report,
    ):
        warnings = []

        if not isinstance(
            regime_report,
            dict,
        ):
            return warnings

        for category, value in regime_report.items():

            if isinstance(value, dict):

                status = str(
                    value.get(
                        "status",
                        "",
                    )
                ).upper()

                if status == "WEAK":
                    warnings.append(
                        f"{category}: WEAK"
                    )

            elif isinstance(value, list):

                for item in value:

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    status = str(
                        item.get(
                            "status",
                            "",
                        )
                    ).upper()

                    if status == "WEAK":

                        label = (
                            item.get(
                                "direction"
                            )
                            or item.get(
                                "trend_regime"
                            )
                            or item.get(
                                "volatility_regime"
                            )
                            or category
                        )

                        warnings.append(
                            f"{category}/{label}: WEAK"
                        )

        return warnings

    def evaluate(
        self,
        paper_report: Dict[str, Any],
        regime_report: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        if not isinstance(
            paper_report,
            dict,
        ):
            raise ValueError(
                "paper_report must be a dictionary."
            )

        if paper_report.get("status") != "COMPLETE":
            raise ValueError(
                "Paper trading report is not complete."
            )

        performance = paper_report.get(
            "performance",
            {},
        )

        account = paper_report.get(
            "account",
            {},
        )

        risk = paper_report.get(
            "risk",
            {},
        )

        trades = paper_report.get(
            "trades",
            [],
        )

        if not isinstance(
            performance,
            dict,
        ):
            performance = {}

        if not isinstance(
            account,
            dict,
        ):
            account = {}

        if not isinstance(
            risk,
            dict,
        ):
            risk = {}

        if not isinstance(
            trades,
            list,
        ):
            trades = []

        # ---------------------------------------------------------
        # Performance fields
        # ---------------------------------------------------------

        trade_count = self._integer(
            self._get_first_value(
                performance,
                [
                    "trades",
                    "total_trades",
                ],
                len(trades),
            )
        )

        wins = self._integer(
            self._get_first_value(
                performance,
                [
                    "wins",
                    "winning_trades",
                ],
                0,
            )
        )

        losses = self._integer(
            self._get_first_value(
                performance,
                [
                    "losses",
                    "losing_trades",
                ],
                0,
            )
        )

        win_rate = self._number(
            performance.get(
                "win_rate",
                0.0,
            )
        )

        profit_factor = self._number(
            performance.get(
                "profit_factor",
                0.0,
            )
        )

        total_pnl = self._number(
            self._get_first_value(
                performance,
                [
                    "total_pnl",
                    "pnl",
                ],
                0.0,
            )
        )

        # ---------------------------------------------------------
        # Drawdown
        # ---------------------------------------------------------

        maximum_drawdown = self._number(
            self._get_first_value(
                performance,
                [
                    "maximum_drawdown",
                    "max_drawdown",
                ],
                self._get_first_value(
                    account,
                    [
                        "max_drawdown",
                        "maximum_drawdown",
                    ],
                    0.0,
                ),
            )
        )

        # ---------------------------------------------------------
        # Account
        # ---------------------------------------------------------

        initial_balance = self._number(
            account.get(
                "initial_balance",
                0.0,
            )
        )

        final_balance = self._number(
            account.get(
                "final_balance",
                0.0,
            )
        )

        # ---------------------------------------------------------
        # Trade-level risk
        # ---------------------------------------------------------

        maximum_losing_streak = (
            self._calculate_losing_streak(
                trades
            )
        )

        current_losing_streak = (
            self._calculate_current_losing_streak(
                trades
            )
        )

        blocked_ratio = (
            self._calculate_blocked_ratio(
                risk
            )
        )

        reasons = []
        warnings = []

        # ---------------------------------------------------------
        # Status evaluation
        # ---------------------------------------------------------

        if trade_count < self.minimum_trades:

            reasons.append(
                f"Only {trade_count} trades; "
                f"{self.minimum_trades} required."
            )

            status = "INSUFFICIENT_DATA"

        else:

            if (
                profit_factor
                < self.warning_profit_factor
            ):
                reasons.append(
                    "Profit factor is below "
                    "the warning threshold."
                )

            elif (
                profit_factor
                < self.healthy_profit_factor
            ):
                warnings.append(
                    "Profit factor is positive "
                    "but below the healthy threshold."
                )

            if (
                win_rate
                < self.warning_win_rate
            ):
                reasons.append(
                    "Win rate is below "
                    "the warning threshold."
                )

            elif (
                win_rate
                < self.healthy_win_rate
            ):
                warnings.append(
                    "Win rate is below "
                    "the healthy threshold."
                )

            if (
                maximum_drawdown
                >= self.maximum_drawdown
            ):
                reasons.append(
                    "Maximum drawdown reached "
                    "the configured pause threshold."
                )

            elif (
                maximum_drawdown
                >= self.warning_drawdown
            ):
                warnings.append(
                    "Maximum drawdown is elevated."
                )

            if (
                maximum_losing_streak
                > self.maximum_losing_streak
            ):
                reasons.append(
                    "Maximum losing streak exceeded "
                    "the configured threshold."
                )

            elif (
                current_losing_streak
                >= self.maximum_losing_streak
            ):
                warnings.append(
                    "Current losing streak is elevated."
                )

            if (
                blocked_ratio
                > self.maximum_blocked_entry_ratio
            ):
                warnings.append(
                    "A large proportion of entries "
                    "were blocked by risk controls."
                )

            regime_warnings = (
                self._extract_regime_warnings(
                    regime_report
                )
            )

            warnings.extend(
                regime_warnings
            )

            if reasons:
                status = "PAUSED"

            elif warnings:
                status = "WARNING"

            else:
                status = "HEALTHY"

        return {
            "status": status,

            "strategy_name": paper_report.get(
                "strategy_name",
                "UNKNOWN",
            ),

            "mode": paper_report.get(
                "mode",
                "UNKNOWN",
            ),

            "live_trading": paper_report.get(
                "live_trading",
                False,
            ),

            "metrics": {
                "trades": trade_count,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_pnl": total_pnl,
                "initial_balance": initial_balance,
                "final_balance": final_balance,
                "maximum_drawdown": maximum_drawdown,
                "maximum_losing_streak": (
                    maximum_losing_streak
                ),
                "current_losing_streak": (
                    current_losing_streak
                ),
                "blocked_entries": (
                    self._integer(
                        self._get_first_value(
                            risk,
                            [
                                "blocked_entries",
                                "blocked",
                            ],
                            0,
                        )
                    )
                ),
                "allowed_entries": (
                    self._integer(
                        self._get_first_value(
                            risk,
                            [
                                "allowed_entries",
                                "allowed",
                            ],
                            0,
                        )
                    )
                ),
                "blocked_entry_ratio": (
                    blocked_ratio
                ),
            },

            "reasons": reasons,

            "warnings": warnings,

            "thresholds": {
                "minimum_trades": (
                    self.minimum_trades
                ),
                "healthy_profit_factor": (
                    self.healthy_profit_factor
                ),
                "warning_profit_factor": (
                    self.warning_profit_factor
                ),
                "healthy_win_rate": (
                    self.healthy_win_rate
                ),
                "warning_win_rate": (
                    self.warning_win_rate
                ),
                "maximum_drawdown": (
                    self.maximum_drawdown
                ),
                "warning_drawdown": (
                    self.warning_drawdown
                ),
                "maximum_losing_streak": (
                    self.maximum_losing_streak
                ),
                "maximum_blocked_entry_ratio": (
                    self.maximum_blocked_entry_ratio
                ),
            },

            "status_is_safe_for_paper": (
                status == "HEALTHY"
            ),

            "status_requires_review": (
                status
                in {
                    "WARNING",
                    "PAUSED",
                }
            ),

            "status": status,
        }

    @staticmethod
    def print_report(
        report: Dict[str, Any],
    ) -> None:

        print()
        print("=" * 90)
        print("PAPER TRADING MONITOR")
        print("=" * 90)

        print(
            f"Strategy             : "
            f"{report.get('strategy_name', 'UNKNOWN')}"
        )

        print(
            f"Mode                 : "
            f"{report.get('mode', 'UNKNOWN')}"
        )

        print(
            f"Live trading         : "
            f"{report.get('live_trading', False)}"
        )

        print(
            f"Monitor status       : "
            f"{report.get('status', 'UNKNOWN')}"
        )

        metrics = report.get(
            "metrics",
            {},
        )

        print()
        print("PERFORMANCE")
        print("-" * 90)

        print(
            f"Trades               : "
            f"{metrics.get('trades', 0)}"
        )

        print(
            f"Wins                 : "
            f"{metrics.get('wins', 0)}"
        )

        print(
            f"Losses               : "
            f"{metrics.get('losses', 0)}"
        )

        print(
            f"Win rate             : "
            f"{metrics.get('win_rate', 0.0):.2%}"
        )

        print(
            f"Profit factor        : "
            f"{metrics.get('profit_factor', 0.0):.4f}"
        )

        print(
            f"Total P&L            : "
            f"{metrics.get('total_pnl', 0.0):.2f}"
        )

        print(
            f"Initial balance      : "
            f"{metrics.get('initial_balance', 0.0):.2f}"
        )

        print(
            f"Final balance        : "
            f"{metrics.get('final_balance', 0.0):.2f}"
        )

        print(
            f"Maximum drawdown     : "
            f"{metrics.get('maximum_drawdown', 0.0):.2%}"
        )

        print()
        print("RISK")
        print("-" * 90)

        print(
            f"Maximum losing streak: "
            f"{metrics.get('maximum_losing_streak', 0)}"
        )

        print(
            f"Current losing streak: "
            f"{metrics.get('current_losing_streak', 0)}"
        )

        print(
            f"Blocked entries      : "
            f"{metrics.get('blocked_entries', 0)}"
        )

        print(
            f"Allowed entries      : "
            f"{metrics.get('allowed_entries', 0)}"
        )

        print(
            f"Blocked ratio        : "
            f"{metrics.get('blocked_entry_ratio', 0.0):.2%}"
        )

        reasons = report.get(
            "reasons",
            [],
        )

        warnings = report.get(
            "warnings",
            [],
        )

        if reasons:
            print()
            print("PAUSE REASONS")
            print("-" * 90)

            for reason in reasons:
                print(
                    f" - {reason}"
                )

        if warnings:
            print()
            print("WARNINGS")
            print("-" * 90)

            for warning in warnings:
                print(
                    f" - {warning}"
                )

        print()
        print("=" * 90)