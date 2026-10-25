from __future__ import annotations

from typing import Any, Dict, Callable

import pandas as pd

from engines.backtest import BacktestEngine


class PaperTradingEngine:
    """
    Historical paper-trading simulator.

    This engine is deliberately simulation-only. It does not:
        - connect to a broker
        - send orders
        - access a live account
        - place real trades

    The existing BacktestEngine performs the candle-by-candle
    trade simulation. This class provides a dedicated paper-
    trading interface around that proven engine.
    """

    def __init__(
        self,
        initial_balance: float = 10_000.0,
        risk_per_trade: float = 0.01,
        stop_atr_multiplier: float = 2.0,
        take_profit_ratio: float = 2.0,
        commission_per_trade: float = 0.0,
        slippage_per_trade: float = 0.0,
        news_events=None,
        comparison_df=None,
        comparison_data=None,
        correlation_window: int = 20,
        maximum_absolute_correlation: float = 0.80,
        news_before_minutes: float = 30.0,
        news_after_minutes: float = 15.0,
        risk_engine=None,
    ):
        self.initial_balance = float(initial_balance)
        self.risk_per_trade = float(risk_per_trade)
        self.stop_atr_multiplier = float(
            stop_atr_multiplier
        )
        self.take_profit_ratio = float(
            take_profit_ratio
        )
        self.commission_per_trade = float(
            commission_per_trade
        )
        self.slippage_per_trade = float(
            slippage_per_trade
        )

        self.news_events = news_events or []
        self.comparison_df = comparison_df
        self.comparison_data = comparison_data
        self.correlation_window = int(
            correlation_window
        )
        self.maximum_absolute_correlation = float(
            maximum_absolute_correlation
        )
        self.news_before_minutes = float(
            news_before_minutes
        )
        self.news_after_minutes = float(
            news_after_minutes
        )
        self.risk_engine = risk_engine

    @staticmethod
    def _clean_timestamp_column(
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        result = data.copy()

        if "timestamp" not in result.columns:
            if "datetime" in result.columns:
                result = result.rename(
                    columns={"datetime": "timestamp"}
                )
            else:
                raise ValueError(
                    "Paper trading data must contain "
                    "'timestamp' or 'datetime'."
                )

        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            errors="coerce",
        )

        result = result.dropna(
            subset=["timestamp"]
        )

        result = (
            result
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        return result

    @staticmethod
    def _validate_market_columns(
        data: pd.DataFrame,
    ) -> None:
        required = {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        }

        missing = sorted(
            required - set(data.columns)
        )

        if missing:
            raise ValueError(
                "Missing required market columns: "
                + ", ".join(missing)
            )

    @staticmethod
    def _validate_signals(
        data: pd.DataFrame,
    ) -> None:
        if "signal" not in data.columns:
            raise ValueError(
                "Paper trading data must contain a "
                "'signal' column."
            )

        valid = data["signal"].astype(str).str.upper()

        invalid = ~valid.isin(
            ["LONG", "SHORT", "NO_SIGNAL"]
        )

        if invalid.any():
            invalid_values = sorted(
                set(
                    valid.loc[invalid].tolist()
                )
            )

            raise ValueError(
                "Unknown signal values found: "
                + ", ".join(invalid_values)
            )

    @staticmethod
    def _apply_strategy_transform(
        data: pd.DataFrame,
        strategy_transform: Callable[
            [pd.DataFrame],
            pd.DataFrame,
        ] | None,
    ) -> pd.DataFrame:
        if strategy_transform is None:
            return data.copy()

        transformed = strategy_transform(
            data.copy()
        )

        if transformed is None:
            raise ValueError(
                "Strategy transform returned None."
            )

        return transformed

    def _create_backtester(self) -> BacktestEngine:
        return BacktestEngine(
            initial_balance=self.initial_balance,
            risk_per_trade=self.risk_per_trade,
            stop_atr_multiplier=self.stop_atr_multiplier,
            take_profit_ratio=self.take_profit_ratio,
            commission_per_trade=(
                self.commission_per_trade
            ),
            slippage_per_trade=(
                self.slippage_per_trade
            ),
            news_events=self.news_events,
            comparison_df=self.comparison_df,
            comparison_data=self.comparison_data,
            correlation_window=self.correlation_window,
            maximum_absolute_correlation=(
                self.maximum_absolute_correlation
            ),
            risk_engine=self.risk_engine,
            news_before_minutes=(
                self.news_before_minutes
            ),
            news_after_minutes=(
                self.news_after_minutes
            ),
        )

    @staticmethod
    def _count_signal_rows(
        data: pd.DataFrame,
    ) -> int:
        signals = (
            data["signal"]
            .astype(str)
            .str.upper()
        )

        return int(
            signals.isin(
                ["LONG", "SHORT"]
            ).sum()
        )

    @staticmethod
    def _count_blocked_signals(
        original_data: pd.DataFrame,
        transformed_data: pd.DataFrame,
    ) -> int:
        original = (
            original_data["signal"]
            .astype(str)
            .str.upper()
            .isin(["LONG", "SHORT"])
        )

        transformed = (
            transformed_data["signal"]
            .astype(str)
            .str.upper()
            .isin(["LONG", "SHORT"])
        )

        return int(
            (
                original
                & ~transformed
            ).sum()
        )

    @staticmethod
    def _summarize_trades(
        trades,
    ) -> Dict[str, Any]:
        if not trades:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
            }

        pnl = pd.to_numeric(
            pd.Series(
                [
                    trade.get("pnl", 0.0)
                    for trade in trades
                ]
            ),
            errors="coerce",
        ).fillna(0.0)

        wins = int(
            (pnl > 0).sum()
        )

        losses = int(
            (pnl < 0).sum()
        )

        gross_profit = float(
            pnl[pnl > 0].sum()
        )

        gross_loss = float(
            -pnl[pnl < 0].sum()
        )

        if gross_loss > 0:
            profit_factor = (
                gross_profit
                / gross_loss
            )
        elif gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        return {
            "trades": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (
                wins / len(trades)
            ),
            "profit_factor": float(
                profit_factor
            ),
            "total_pnl": float(
                pnl.sum()
            ),
        }

    @staticmethod
    def _count_risk_events(
        risk_events,
    ) -> Dict[str, int]:
        blocked = 0
        allowed = 0

        for event in risk_events:
            action = str(
                event.get(
                    "action",
                    "",
                )
            ).upper()

            if action == "BLOCKED":
                blocked += 1

            elif action == "ENTRY_ALLOWED":
                allowed += 1

        return {
            "blocked": blocked,
            "allowed": allowed,
        }

    def run(
        self,
        analyzed_data: pd.DataFrame,
        strategy_name: str = "PAPER_STRATEGY",
        strategy_transform: Callable[
            [pd.DataFrame],
            pd.DataFrame,
        ] | None = None,
    ) -> Dict[str, Any]:
        if analyzed_data is None:
            raise ValueError(
                "analyzed_data cannot be None."
            )

        if analyzed_data.empty:
            raise ValueError(
                "analyzed_data cannot be empty."
            )

        original = self._clean_timestamp_column(
            analyzed_data
        )

        self._validate_market_columns(
            original
        )

        transformed = (
            self._apply_strategy_transform(
                original,
                strategy_transform,
            )
        )

        transformed = (
            self._clean_timestamp_column(
                transformed
            )
        )

        self._validate_market_columns(
            transformed
        )

        self._validate_signals(
            transformed
        )

        original_signal_count = (
            self._count_signal_rows(
                original
            )
        )

        transformed_signal_count = (
            self._count_signal_rows(
                transformed
            )
        )

        strategy_blocked = (
            self._count_blocked_signals(
                original,
                transformed,
            )
        )

        backtester = self._create_backtester()

        simulation = backtester.run(
            transformed
        )

        trades = simulation.get(
            "trades",
            [],
        )

        risk_events = simulation.get(
            "risk_events",
            [],
        )

        trade_summary = (
            self._summarize_trades(
                trades
            )
        )

        risk_summary = (
            self._count_risk_events(
                risk_events
            )
        )

        return {
            "mode": "PAPER",
            "live_trading": False,
            "strategy_name": strategy_name,

            "data": {
                "rows": len(transformed),
                "start": transformed[
                    "timestamp"
                ].iloc[0],
                "end": transformed[
                    "timestamp"
                ].iloc[-1],
                "original_signal_count": (
                    original_signal_count
                ),
                "strategy_signal_count": (
                    transformed_signal_count
                ),
                "strategy_blocked_signals": (
                    strategy_blocked
                ),
            },

            "account": {
                "initial_balance": simulation.get(
                    "initial_balance",
                    self.initial_balance,
                ),
                "final_balance": simulation.get(
                    "final_balance",
                    self.initial_balance,
                ),
                "max_drawdown": simulation.get(
                    "max_drawdown",
                    0.0,
                ),
            },

            "performance": trade_summary,

            "risk": {
                "blocked_entries": (
                    risk_summary["blocked"]
                ),
                "allowed_entries": (
                    risk_summary["allowed"]
                ),
                "risk_event_count": len(
                    risk_events
                ),
            },

            "trades": trades,
            "risk_events": risk_events,
            "equity_curve": simulation.get(
                "equity_curve",
                [],
            ),

            "status": "COMPLETE",
        }

    @staticmethod
    def print_report(
        report: Dict[str, Any],
    ) -> None:
        print()
        print("=" * 90)
        print("PAPER TRADING REPORT")
        print("=" * 90)

        if report.get("status") != "COMPLETE":
            print("Paper simulation did not complete.")
            return

        print(
            f"Mode                 : "
            f"{report.get('mode', 'UNKNOWN')}"
        )

        print(
            f"Live trading         : "
            f"{report.get('live_trading', True)}"
        )

        print(
            f"Strategy             : "
            f"{report.get('strategy_name', 'UNKNOWN')}"
        )

        data = report.get(
            "data",
            {},
        )

        account = report.get(
            "account",
            {},
        )

        performance = report.get(
            "performance",
            {},
        )

        risk = report.get(
            "risk",
            {},
        )

        print(
            f"Rows                 : "
            f"{data.get('rows', 0)}"
        )

        print(
            f"Strategy signals     : "
            f"{data.get('strategy_signal_count', 0)}"
        )

        print(
            f"Strategy blocked     : "
            f"{data.get('strategy_blocked_signals', 0)}"
        )

        print(
            f"Initial balance      : "
            f"{account.get('initial_balance', 0.0):.2f}"
        )

        print(
            f"Final balance        : "
            f"{account.get('final_balance', 0.0):.2f}"
        )

        print(
            f"Total trades         : "
            f"{performance.get('trades', 0)}"
        )

        print(
            f"Win rate             : "
            f"{performance.get('win_rate', 0.0):.2%}"
        )

        print(
            f"Profit factor        : "
            f"{performance.get('profit_factor', 0.0):.4f}"
        )

        print(
            f"Total P&L            : "
            f"{performance.get('total_pnl', 0.0):.2f}"
        )

        print(
            f"Maximum drawdown     : "
            f"{account.get('max_drawdown', 0.0):.2%}"
        )

        print(
            f"Blocked entries      : "
            f"{risk.get('blocked_entries', 0)}"
        )

        print(
            f"Allowed entries      : "
            f"{risk.get('allowed_entries', 0)}"
        )

        print()
        print("=" * 90)