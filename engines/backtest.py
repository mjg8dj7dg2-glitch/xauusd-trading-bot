import pandas as pd

from engines.risk import RiskEngine
from engines.news import check_news_risk
from engines.correlation import calculate_correlation
from engines.memory_report import MemoryReport


class BacktestEngine:

    def __init__(
        self,
        initial_balance=10000.0,
        risk_per_trade=0.01,
        stop_atr_multiplier=2.0,
        take_profit_ratio=2.0,
        commission_per_trade=0.0,
        slippage_per_trade=0.0,
        news_events=None,
        comparison_df=None,
        comparison_data=None,
        correlation_window=20,
        maximum_absolute_correlation=0.80,
        risk_engine=None,
        news_before_minutes=30,
        news_after_minutes=15,
        maximum_consecutive_losses=5,
        losing_streak_cooldown_candles=12,
    ):
        self.initial_balance = float(initial_balance)
        self.balance = float(initial_balance)

        self.risk_per_trade = float(risk_per_trade)
        self.stop_atr_multiplier = float(stop_atr_multiplier)
        self.take_profit_ratio = float(take_profit_ratio)

        self.commission_per_trade = float(
            commission_per_trade
        )
        self.slippage_per_trade = float(
            slippage_per_trade
        )

        self.news_events = news_events or []

        self.news_before_minutes = float(
            news_before_minutes
        )
        self.news_after_minutes = float(
            news_after_minutes
        )

        if comparison_df is not None:
            self.comparison_df = comparison_df
        else:
            self.comparison_df = comparison_data

        self.correlation_window = int(
            correlation_window
        )
        self.maximum_absolute_correlation = float(
            maximum_absolute_correlation
        )

        self.peak_balance = self.initial_balance
        self.daily_starting_balance = self.initial_balance
        self.daily_pnl = 0.0

        self.trades = []
        self.risk_events = []

        self.current_trade = None
        self.current_trade_context = {}

        self.maximum_consecutive_losses = int(maximum_consecutive_losses)
        if self.maximum_consecutive_losses < 1:
            raise ValueError("maximum_consecutive_losses must be at least 1")
        self.losing_streak_cooldown_candles = int(
            losing_streak_cooldown_candles
        )
        if self.losing_streak_cooldown_candles < 1:
            raise ValueError(
                "losing_streak_cooldown_candles must be at least 1"
            )
        self.current_losing_streak = 0
        self.losing_streak_paused = False
        self.losing_streak_pause_until_index = None
        self._current_candle_index = None

        if risk_engine is not None:
            self.risk_engine = risk_engine
        else:
            self.risk_engine = RiskEngine(
                max_risk_per_trade=self.risk_per_trade
            )

        self.memory_report_engine = MemoryReport(
            minimum_similarity=0.60,
            max_similar_trades=5,
            minimum_losses=3,
            minimum_occurrences=2,
            minimum_percentage=0.50,
        )

    def _update_losing_streak(self, pnl, candle_index=None):
        pnl = float(pnl)
        if pnl < 0:
            self.current_losing_streak += 1
        elif pnl > 0:
            self.current_losing_streak = 0
            self.losing_streak_paused = False
            self.losing_streak_pause_until_index = None

        if (
            pnl < 0
            and self.current_losing_streak >= self.maximum_consecutive_losses
            and not self.losing_streak_paused
        ):
            self.losing_streak_paused = True
            if candle_index is not None:
                self.losing_streak_pause_until_index = (
                    candle_index + self.losing_streak_cooldown_candles + 1
                )

    def _safe_float(self, value, default=None):
        try:
            value = float(value)

            if pd.isna(value):
                return default

            return value

        except (TypeError, ValueError):
            return default

    def _get_value(self, row, name, default=None):
        try:
            value = row[name]

            if pd.isna(value):
                return default

            return value

        except (KeyError, TypeError):
            return default

    def prepare_position(self, row, direction):
        entry_price = self._safe_float(
            self._get_value(row, "close")
        )

        atr = self._safe_float(
            self._get_value(row, "atr")
        )

        if entry_price is None:
            return None

        if atr is None or atr <= 0:
            return None

        direction = str(direction).upper()

        stop_distance = (
            atr * self.stop_atr_multiplier
        )

        target_distance = (
            stop_distance * self.take_profit_ratio
        )

        if direction == "LONG":

            stop_loss = (
                entry_price - stop_distance
            )

            take_profit = (
                entry_price + target_distance
            )

        elif direction == "SHORT":

            stop_loss = (
                entry_price + stop_distance
            )

            take_profit = (
                entry_price - target_distance
            )

        else:
            return None

        quantity = (
            self.risk_engine.calculate_position_size(
                account_balance=self.balance,
                entry_price=entry_price,
                stop_loss=stop_loss,
                contract_value=1.0,
            )
        )

        if quantity <= 0:
            return None

        self.current_trade_context = {
            "direction": direction,
            "trend_regime": self._get_value(
                row,
                "trend_regime",
                "UNKNOWN",
            ),
            "volatility_regime": self._get_value(
                row,
                "volatility_regime",
                "UNKNOWN",
            ),
            "rsi": self._get_value(row, "rsi"),
            "atr": self._get_value(row, "atr"),
            "ema": self._get_value(row, "ema"),
            "sma": self._get_value(row, "sma"),
            "signal_strength": self._get_value(
                row,
                "signal_strength",
            ),
            "signal_reason": self._get_value(
                row,
                "signal_reason",
                "",
            ),
        }

        return {
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "quantity": quantity,
        }

    def check_news(self, current_time):
        return check_news_risk(
            current_time=current_time,
            events=self.news_events,
            before_minutes=self.news_before_minutes,
            after_minutes=self.news_after_minutes,
        )

    def check_correlation(
        self,
        primary_df,
        current_timestamp,
    ):
        if self.comparison_df is None:
            return (
                True,
                "No comparison market supplied",
                None,
            )

        try:
            correlation_df = calculate_correlation(
                primary_df,
                self.comparison_df,
                window=self.correlation_window,
            )

            if correlation_df.empty:
                return (
                    True,
                    "Correlation unavailable",
                    None,
                )

            matches = correlation_df[
                correlation_df["timestamp"]
                <= pd.to_datetime(current_timestamp)
            ]

            if matches.empty:
                return (
                    True,
                    "Correlation unavailable",
                    None,
                )

            latest = matches.iloc[-1]

            correlation = latest.get(
                "correlation"
            )

            if pd.isna(correlation):
                return (
                    True,
                    "Correlation unavailable",
                    None,
                )

            correlation = float(correlation)

            limit = self.maximum_absolute_correlation

            if abs(correlation) >= limit:
                return (
                    False,
                    (
                        "Correlation risk: "
                        f"absolute correlation is "
                        f"{correlation:.3f}, "
                        f"above limit {limit:.2f}"
                    ),
                    correlation,
                )

            return (
                True,
                (
                    "Correlation check passed "
                    f"({correlation:.3f})"
                ),
                correlation,
            )

        except Exception as error:
            return (
                True,
                (
                    "Correlation calculation "
                    f"unavailable: {error}"
                ),
                None,
            )

    def check_risk(self, df, row, signal):
        working_df = df.loc[:row.name].copy()

        allowed, reasons = (
            self.risk_engine.check_signal(
                df=working_df,
                signal=signal,
                account_balance=self.balance,
                peak_balance=self.peak_balance,
                daily_pnl=self.daily_pnl,
                starting_daily_balance=(
                    self.daily_starting_balance
                ),
            )
        )

        if not isinstance(reasons, list):
            reasons = [str(reasons)]

        current_time = self._get_value(
            row,
            "timestamp",
        )

        (
            news_allowed,
            news_message,
            news_event,
        ) = self.check_news(current_time)

        reasons.append(news_message)

        if not news_allowed:
            allowed = False

        (
            correlation_allowed,
            correlation_message,
            correlation,
        ) = self.check_correlation(
            df,
            current_time,
        )

        reasons.append(correlation_message)

        if not correlation_allowed:
            allowed = False

        return (
            allowed,
            reasons,
            news_event,
            correlation,
        )

    def analyze_trade_memory(self, row, signal):
        current_trade = {
            "direction": signal,
            "trend_regime": self._get_value(
                row,
                "trend_regime",
            ),
            "volatility_regime": self._get_value(
                row,
                "volatility_regime",
            ),
            "rsi": self._get_value(
                row,
                "rsi",
            ),
            "atr": self._get_value(
                row,
                "atr",
            ),
            "ema": self._get_value(
                row,
                "ema",
            ),
            "sma": self._get_value(
                row,
                "sma",
            ),
        }

        return self.memory_report_engine.build_report(
            current_trade=current_trade,
            historical_trades=self.trades,
            recent_count=10,
        )

    def _update_trade_excursions(self, row):
        if self.current_trade is None:
            return

        high = self._safe_float(
            self._get_value(row, "high")
        )

        low = self._safe_float(
            self._get_value(row, "low")
        )

        if high is None or low is None:
            return

        trade = self.current_trade

        entry_price = trade["entry_price"]
        direction = trade["direction"]

        if direction == "LONG":

            favorable_move = (
                high - entry_price
            )

            adverse_move = (
                entry_price - low
            )

        else:

            favorable_move = (
                entry_price - low
            )

            adverse_move = (
                high - entry_price
            )

        trade["max_favorable_price_move"] = max(
            trade.get(
                "max_favorable_price_move",
                0.0,
            ),
            favorable_move,
        )

        trade["max_adverse_price_move"] = max(
            trade.get(
                "max_adverse_price_move",
                0.0,
            ),
            adverse_move,
        )

        quantity = trade["quantity"]

        trade["mfe"] = (
            trade["max_favorable_price_move"]
            * quantity
        )

        trade["mae"] = (
            trade["max_adverse_price_move"]
            * quantity
        )

    def _complete_trade(
        self,
        row,
        exit_price,
        exit_reason,
    ):
        if self.current_trade is None:
            return None

        trade = self.current_trade

        entry_price = trade["entry_price"]
        quantity = trade["quantity"]
        direction = trade["direction"]

        exit_price = float(exit_price)

        if direction == "LONG":

            gross_pnl = (
                exit_price - entry_price
            ) * quantity

        else:

            gross_pnl = (
                entry_price - exit_price
            ) * quantity

        commission = (
            self.commission_per_trade
        )

        slippage = (
            self.slippage_per_trade
            * quantity
        )

        pnl = (
            gross_pnl
            - commission
            - slippage
        )

        self._update_trade_excursions(row)

        completed_trade = {
            # Primary names
            "direction": direction,
            "entry_time": trade["entry_time"],
            "exit_time": self._get_value(
                row,
                "timestamp",
            ),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "stop_loss": trade["stop_loss"],
            "take_profit": trade["take_profit"],
            "quantity": quantity,
            "pnl": pnl,
            "result": (
                "WIN"
                if pnl > 0
                else "LOSS"
                if pnl < 0
                else "BREAKEVEN"
            ),
            "exit_reason": exit_reason,

            # Compatibility aliases
            "signal": direction,

            # Execution costs
            "commission": commission,
            "slippage": slippage,

            # Risk information
            "risk_checks": trade.get(
                "risk_checks",
                [],
            ),

            # Market context
            "trend_regime": (
                self.current_trade_context.get(
                    "trend_regime",
                    "UNKNOWN",
                )
            ),
            "volatility_regime": (
                self.current_trade_context.get(
                    "volatility_regime",
                    "UNKNOWN",
                )
            ),
            "rsi": (
                self.current_trade_context.get(
                    "rsi"
                )
            ),
            "atr": (
                self.current_trade_context.get(
                    "atr"
                )
            ),
            "ema": (
                self.current_trade_context.get(
                    "ema"
                )
            ),
            "sma": (
                self.current_trade_context.get(
                    "sma"
                )
            ),
            "signal_strength": (
                self.current_trade_context.get(
                    "signal_strength"
                )
            ),
            "signal_reason": (
                self.current_trade_context.get(
                    "signal_reason",
                    "",
                )
            ),

            # Cross-market / macro context
            "correlation": trade.get(
                "correlation"
            ),
            "news_event": trade.get(
                "news_event"
            ),

            # Historical trade memory
            "memory_report": (
                self.current_trade_context.get(
                    "memory_report"
                )
            ),

            # Trade excursion diagnostics
            "mfe": trade.get(
                "mfe",
                0.0,
            ),
            "mae": trade.get(
                "mae",
                0.0,
            ),
            "max_favorable_price_move": trade.get(
                "max_favorable_price_move",
                0.0,
            ),
            "max_adverse_price_move": trade.get(
                "max_adverse_price_move",
                0.0,
            ),
        }

        self.balance += pnl

        self.peak_balance = max(
            self.peak_balance,
            self.balance,
        )

        self.daily_pnl += pnl

        self._update_losing_streak(pnl, self._current_candle_index)

        self.trades.append(
            completed_trade
        )

        self.current_trade = None
        self.current_trade_context = {}

        return completed_trade

    def check_exit(self, row):
        if self.current_trade is None:
            return None

        trade = self.current_trade

        self._update_trade_excursions(row)

        high = self._safe_float(
            self._get_value(row, "high")
        )

        low = self._safe_float(
            self._get_value(row, "low")
        )

        if high is None or low is None:
            return None

        direction = trade["direction"]

        if direction == "LONG":

            if low <= trade["stop_loss"]:
                return self._complete_trade(
                    row,
                    trade["stop_loss"],
                    "STOP_LOSS",
                )

            if high >= trade["take_profit"]:
                return self._complete_trade(
                    row,
                    trade["take_profit"],
                    "TAKE_PROFIT",
                )

        elif direction == "SHORT":

            if high >= trade["stop_loss"]:
                return self._complete_trade(
                    row,
                    trade["stop_loss"],
                    "STOP_LOSS",
                )

            if low <= trade["take_profit"]:
                return self._complete_trade(
                    row,
                    trade["take_profit"],
                    "TAKE_PROFIT",
                )

        return None

    def force_close_at_end(self, row):
        if self.current_trade is None:
            return None

        exit_price = self._safe_float(
            self._get_value(row, "close")
        )

        if exit_price is None:
            return None

        return self._complete_trade(
            row,
            exit_price,
            "END_OF_DATA",
        )

    def run(self, df):
        if df is None or df.empty:
            return {
                "initial_balance": self.initial_balance,
                "final_balance": self.balance,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "trades": [],
                "risk_events": [],
                "equity_curve": [],
            }

        data = df.copy()

        if "timestamp" in data.columns:
            data["timestamp"] = pd.to_datetime(
                data["timestamp"]
            )

        data = (
            data
            .reset_index(drop=True)
        )

        if "timestamp" in data.columns:
            data = (
                data
                .sort_values("timestamp")
                .reset_index(drop=True)
            )

        self.balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.daily_starting_balance = self.initial_balance
        self.daily_pnl = 0.0

        self.trades = []
        self.risk_events = []
        self.current_trade = None
        self.current_trade_context = {}
        self.current_losing_streak = 0
        self.losing_streak_paused = False
        self.losing_streak_pause_until_index = None
        self._current_candle_index = None

        equity_curve = []

        for index in range(len(data)):

            self._current_candle_index = index
            if (
                self.losing_streak_paused
                and self.losing_streak_pause_until_index is not None
                and index >= self.losing_streak_pause_until_index
            ):
                self.losing_streak_paused = False
                self.losing_streak_pause_until_index = None
                self.current_losing_streak = 0

            row = data.iloc[index]

            if index > 0:

                previous_row = data.iloc[
                    index - 1
                ]

                current_time = self._get_value(
                    row,
                    "timestamp",
                )

                previous_time = self._get_value(
                    previous_row,
                    "timestamp",
                )

                if (
                    current_time is not None
                    and previous_time is not None
                    and pd.to_datetime(
                        current_time
                    ).date()
                    != pd.to_datetime(
                        previous_time
                    ).date()
                ):
                    self.daily_starting_balance = (
                        self.balance
                    )
                    self.daily_pnl = 0.0

            if self.current_trade is not None:

                completed = self.check_exit(row)

                if completed is not None:
                    equity_curve.append(
                        self.balance
                    )
                    continue

            if self.current_trade is not None:

                equity_curve.append(
                    self.balance
                )
                continue

            signal = str(
                self._get_value(
                    row,
                    "signal",
                    "NO_SIGNAL",
                )
            ).upper()

            if signal not in [
                "LONG",
                "SHORT",
            ]:
                equity_curve.append(
                    self.balance
                )
                continue

            if self.losing_streak_paused:
                self.risk_events.append({
                    "timestamp": self._get_value(row, "timestamp"),
                    "signal": signal,
                    "action": "BLOCKED_LOSING_STREAK",
                    "allowed": False,
                    "reasons": [
                        "BLOCKED_LOSING_STREAK: consecutive-loss threshold reached; cooldown active"
                    ],
                    "news_event": None,
                    "correlation": None,
                    "memory_report": None,
                })
                equity_curve.append(self.balance)
                continue

            (
                allowed,
                reasons,
                news_event,
                correlation,
            ) = self.check_risk(
                data,
                row,
                signal,
            )

            memory_report = (
                self.analyze_trade_memory(
                    row,
                    signal,
                )
            )

            if not allowed:

                
                self.risk_events.append({
                    "timestamp": self._get_value(
                        row,
                        "timestamp",
                    ),
                    "signal": signal,
                    "action": "BLOCKED",
                    "allowed": False,
                    "reasons": reasons,
                    "news_event": news_event,
                    "correlation": correlation,
                    "memory_report": memory_report,
                })

                equity_curve.append(
                    self.balance
                )
                continue


            position = self.prepare_position(
                row,
                signal,
            )

            if position is None:

                
                self.risk_events.append({
                    "timestamp": self._get_value(
                        row,
                        "timestamp",
                    ),
                    "signal": signal,
                    "action": "BLOCKED",
                    "allowed": False,
                    "reasons": [
                        *reasons,
                        "Could not calculate valid position",
                    ],
                    "news_event": news_event,
                    "correlation": correlation,
                    "memory_report": memory_report,
                })

                equity_curve.append(
                    self.balance
                )
                continue

                continue

            self.current_trade_context[
                "correlation"
            ] = correlation

            self.current_trade_context[
                "news_event"
            ] = news_event

            self.current_trade_context[
                "memory_report"
            ] = memory_report

            self.current_trade = {
                **position,

                "entry_time": self._get_value(
                    row,
                    "timestamp",
                ),

                "risk_checks": reasons,

                "correlation": correlation,

                "news_event": news_event,

                "mfe": 0.0,

                "mae": 0.0,

                "max_favorable_price_move": 0.0,

                "max_adverse_price_move": 0.0,
            }

            
                
            self.risk_events.append({
                "timestamp": self._get_value(
                    row,
                    "timestamp",
                ),
                "signal": signal,
                "action": "ENTRY_ALLOWED",
                "allowed": True,
                "reasons": [
                    *reasons,
                    "Entry allowed by all risk filters",
                ],
                "news_event": news_event,
                "correlation": correlation,
                "memory_report": memory_report,
            })

            equity_curve.append(
                self.balance
            )


        # If a trade is still open at the end
        # of the dataset, close it using the
        # final candle close.
        if self.current_trade is not None:

            final_row = data.iloc[-1]

            completed = self.force_close_at_end(
                final_row
            )

            if completed is not None:

                if len(equity_curve) < len(data):
                    equity_curve.append(
                        self.balance
                    )
                elif equity_curve:
                    equity_curve[-1] = (
                        self.balance
                    )

        # Make absolutely sure the equity curve
        # has exactly one value per data row.
        if len(equity_curve) < len(data):

            last_value = self.balance

            while len(equity_curve) < len(data):
                equity_curve.append(
                    last_value
                )

        elif len(equity_curve) > len(data):

            equity_curve = equity_curve[
                :len(data)
            ]

        total_trades = len(self.trades)

        winning_trades = sum(
            1
            for trade in self.trades
            if trade["pnl"] > 0
        )

        losing_trades = sum(
            1
            for trade in self.trades
            if trade["pnl"] < 0
        )

        if total_trades > 0:
            win_rate = (
                winning_trades
                / total_trades
            )
        else:
            win_rate = 0.0

        gross_profit = sum(
            trade["pnl"]
            for trade in self.trades
            if trade["pnl"] > 0
        )

        gross_loss = abs(
            sum(
                trade["pnl"]
                for trade in self.trades
                if trade["pnl"] < 0
            )
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

        if equity_curve:

            equity = pd.Series(
                equity_curve,
                dtype=float,
            )

            running_peak = (
                equity.cummax()
            )

            drawdown = (
                running_peak - equity
            ) / running_peak

            max_drawdown = float(
                drawdown.max()
            )

        else:

            max_drawdown = 0.0

        return {
            "initial_balance": (
                self.initial_balance
            ),
            "final_balance": (
                self.balance
            ),
            "total_trades": (
                total_trades
            ),
            "winning_trades": (
                winning_trades
            ),
            "losing_trades": (
                losing_trades
            ),
            "win_rate": float(
                win_rate
            ),
            "profit_factor": float(
                profit_factor
            ),
            "max_drawdown": float(
                max_drawdown
            ),
            "trades": self.trades,
            "risk_events": self.risk_events,
            "equity_curve": equity_curve,
        }


# Compatibility with older code
Backtester = BacktestEngine