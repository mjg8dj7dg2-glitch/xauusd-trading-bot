import pandas as pd

from engines.market_data import load_csv
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals
from engines.backtest import BacktestEngine
from engines.health_report import HealthReport


class TradingPipeline:

    def __init__(
        self,
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        commission_per_trade=0.0,
        slippage_per_trade=0.0,
        minimum_rows=100,
        news_events=None,
        comparison_df=None,
        comparison_data=None,
        correlation_window=20,
        maximum_absolute_correlation=0.80,
        news_before_minutes=30,
        news_after_minutes=15,
    ):
        self.initial_balance = float(
            initial_balance
        )

        self.risk_per_trade = float(
            risk_per_trade
        )

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

        self.minimum_rows = int(
            minimum_rows
        )

        self.news_events = news_events or []

        self.comparison_df = comparison_df

        if comparison_df is None:
            self.comparison_df = comparison_data

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

    def load_data(self, file_path):
        data = load_csv(file_path)

        if data is None:
            raise ValueError(
                "Market-data loader returned no data."
            )

        if data.empty:
            raise ValueError(
                "Market-data file is empty."
            )

        if len(data) < self.minimum_rows:
            raise ValueError(
                f"Not enough rows. "
                f"Required at least {self.minimum_rows}, "
                f"received {len(data)}."
            )

        return data

    def analyze_market(self, data):
        result = data.copy()

        result = add_technical_features(
            result
        )

        result = add_market_regime(
            result
        )

        result = generate_signals(
            result
        )

        return result

    def run_backtest(self, data):
        backtester = BacktestEngine(
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
            correlation_window=self.correlation_window,
            maximum_absolute_correlation=(
                self.maximum_absolute_correlation
            ),
            news_before_minutes=(
                self.news_before_minutes
            ),
            news_after_minutes=(
                self.news_after_minutes
            ),
        )

        return backtester.run(data)

    def build_health_report(
        self,
        backtest_result,
    ):
        trades = backtest_result.get(
            "trades",
            []
        )

        normalized_trades = []

        for trade in trades:

            normalized_trade = dict(
                trade
            )

            # Make sure the health engines
            # always have a standard result field.
            if "result" not in normalized_trade:

                pnl = float(
                    normalized_trade.get(
                        "pnl",
                        0.0
                    )
                )

                if pnl > 0:
                    normalized_trade[
                        "result"
                    ] = "WIN"

                elif pnl < 0:
                    normalized_trade[
                        "result"
                    ] = "LOSS"

                else:
                    normalized_trade[
                        "result"
                    ] = "BREAKEVEN"

            # Make sure direction exists.
            if not normalized_trade.get(
                "direction"
            ):

                normalized_trade[
                    "direction"
                ] = normalized_trade.get(
                    "signal",
                    "UNKNOWN"
                )

            # Make sure signal exists.
            if not normalized_trade.get(
                "signal"
            ):

                normalized_trade[
                    "signal"
                ] = normalized_trade.get(
                    "direction",
                    "UNKNOWN"
                )

            # Standardize regime fields.
            if not normalized_trade.get(
                "trend_regime"
            ):
                normalized_trade[
                    "trend_regime"
                ] = "UNKNOWN"

            if not normalized_trade.get(
                "volatility_regime"
            ):
                normalized_trade[
                    "volatility_regime"
                ] = "UNKNOWN"

            normalized_trades.append(
                normalized_trade
            )

        # Use the actual completed trades.
        all_trades = normalized_trades

        # Recent trades are chronological.
        recent_count = min(
            20,
            len(all_trades)
        )

        if recent_count > 0:
            recent_trades = all_trades[
                -recent_count:
            ]
        else:
            recent_trades = []

        # Historical trades exclude the
        # recent sample when possible.
        if len(all_trades) > recent_count:
            historical_trades = all_trades[
                :-recent_count
            ]
        else:
            historical_trades = []

        health_report_engine = HealthReport(
            starting_balance=(
                self.initial_balance
            ),
            minimum_recent_trades=5,
            minimum_regime_trades=3,
        )

        report = (
            health_report_engine.build_report(
                historical_trades=(
                    historical_trades
                ),
                recent_trades=(
                    recent_trades
                ),
                all_trades=all_trades,
            )
        )

        return report

    def count_risk_events(
        self,
        backtest_result
    ):
        events = backtest_result.get(
            "risk_events",
            []
        )

        trades = backtest_result.get(
            "trades",
            []
        )

        blocked = 0
        allowed = 0

        for event in events:

            action = str(
                event.get(
                    "action",
                    ""
                )
            ).upper()

            if action == "BLOCKED":
                blocked += 1

            elif action == "ENTRY_ALLOWED":
                allowed += 1

        return {
            "total_events": len(events),
            "blocked": blocked,
            "allowed": allowed,
            "executed_trades": len(trades),
        }

    def build_summary(
        self,
        data,
        backtest_result,
        report,
    ):
        trades = backtest_result.get(
            "trades",
            []
        )

        risk_summary = (
            self.count_risk_events(
                backtest_result
            )
        )

        signal_counts = {}

        if "signal" in data.columns:

            signal_counts = (
                data["signal"]
                .value_counts()
                .to_dict()
            )

        trend_counts = {}

        if "trend_regime" in data.columns:

            trend_counts = (
                data["trend_regime"]
                .value_counts()
                .to_dict()
            )

        volatility_counts = {}

        if "volatility_regime" in data.columns:

            volatility_counts = (
                data["volatility_regime"]
                .value_counts()
                .to_dict()
            )

        strategy_health = report.get(
            "strategy_health",
            {}
        )

        regime_health = report.get(
            "regime_health",
            {}
        )

        regime_statuses = {}

        for regime, result in (
            regime_health.items()
        ):

            regime_statuses[
                regime
            ] = result.get(
                "status",
                "UNKNOWN"
            )

        return {
            "data_rows": len(data),

            "data_start": (
                data["timestamp"].iloc[0]
                if "timestamp" in data.columns
                and len(data) > 0
                else None
            ),

            "data_end": (
                data["timestamp"].iloc[-1]
                if "timestamp" in data.columns
                and len(data) > 0
                else None
            ),

            "signal_counts": signal_counts,

            "trend_regimes": trend_counts,

            "volatility_regimes": (
                volatility_counts
            ),

            "initial_balance": (
                backtest_result.get(
                    "initial_balance",
                    self.initial_balance
                )
            ),

            "final_balance": (
                backtest_result.get(
                    "final_balance",
                    self.initial_balance
                )
            ),

            "total_trades": (
                backtest_result.get(
                    "total_trades",
                    len(trades)
                )
            ),

            "winning_trades": (
                backtest_result.get(
                    "winning_trades",
                    0
                )
            ),

            "losing_trades": (
                backtest_result.get(
                    "losing_trades",
                    0
                )
            ),

            "win_rate": (
                backtest_result.get(
                    "win_rate",
                    0.0
                )
            ),

            "profit_factor": (
                backtest_result.get(
                    "profit_factor",
                    0.0
                )
            ),

            "max_drawdown": (
                backtest_result.get(
                    "max_drawdown",
                    0.0
                )
            ),

            "risk_events": risk_summary,

            "strategy_health": strategy_health,

            "regime_health": regime_health,

            "regime_statuses": regime_statuses,
        }

    def run(
        self,
        file_path,
    ):
        raw_data = self.load_data(
            file_path
        )

        analyzed_data = (
            self.analyze_market(
                raw_data
            )
        )

        backtest_result = (
            self.run_backtest(
                analyzed_data
            )
        )

        health_report = (
            self.build_health_report(
                backtest_result
            )
        )

        summary = self.build_summary(
            data=analyzed_data,
            backtest_result=backtest_result,
            report=health_report,
        )

        return {
            "raw_data": raw_data,

            "data": analyzed_data,

            "backtest": backtest_result,

            "report": health_report,

            "summary": summary,
        }


Pipeline = TradingPipeline