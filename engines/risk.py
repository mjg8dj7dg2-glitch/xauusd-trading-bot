import math
import pandas as pd


class RiskEngine:
    """
    Central risk-control engine.

    This version is designed for backtesting and paper trading.
    It does not place real trades.
    """

    def __init__(
        self,
        max_risk_per_trade=0.01,
        max_drawdown=0.10,
        max_daily_loss=0.03,
        max_position_value=1.0,
    ):
        # 1% risk per trade by default
        self.max_risk_per_trade = max_risk_per_trade

        # 10% maximum account drawdown
        self.max_drawdown = max_drawdown

        # 3% maximum daily loss
        self.max_daily_loss = max_daily_loss

        # Maximum position value as a fraction of account balance.
        # 1.0 = 100% of balance.
        self.max_position_value = max_position_value

        self.kill_switch = False

    def activate_kill_switch(self):
        """Stop all new trading signals."""

        self.kill_switch = True

    def deactivate_kill_switch(self):
        """Allow risk checks again."""

        self.kill_switch = False

    def check_data_quality(self, df):
        """Check whether market data is usable."""

        if df is None:
            return False, "No market data provided"

        if df.empty:
            return False, "Market data is empty"

        required_columns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            return False, f"Missing columns: {missing}"

        price_columns = [
            "open",
            "high",
            "low",
            "close",
        ]

        if df[price_columns].isnull().any().any():
            return False, "Market data contains missing prices"

        if (df["high"] < df["low"]).any():
            return False, "Invalid candle: high below low"

        if (df["high"] < df["open"]).any():
            return False, "Invalid candle: high below open"

        if (df["high"] < df["close"]).any():
            return False, "Invalid candle: high below close"

        if (df["low"] > df["open"]).any():
            return False, "Invalid candle: low above open"

        if (df["low"] > df["close"]).any():
            return False, "Invalid candle: low above close"

        return True, "Data quality check passed"

    def check_volatility(self, volatility_regime):
        """Block trading during extreme volatility."""

        if volatility_regime == "HIGH_VOLATILITY":
            return False, "Trading blocked: high volatility"

        if volatility_regime == "UNKNOWN":
            return False, "Trading blocked: volatility is unknown"

        return True, "Volatility check passed"

    def check_drawdown(
        self,
        current_balance,
        peak_balance,
    ):
        """Check account drawdown."""

        if peak_balance <= 0:
            return False, "Invalid peak balance"

        drawdown = (
            peak_balance - current_balance
        ) / peak_balance

        if drawdown >= self.max_drawdown:
            return False, (
                f"Trading blocked: maximum drawdown reached "
                f"({drawdown:.2%})"
            )

        return True, f"Drawdown check passed ({drawdown:.2%})"

    def check_daily_loss(
        self,
        daily_pnl,
        starting_daily_balance,
    ):
        """Check the daily loss limit."""

        if starting_daily_balance <= 0:
            return False, "Invalid daily starting balance"

        daily_loss = (
            -daily_pnl / starting_daily_balance
        )

        # Only apply the limit when the day is losing.
        if daily_pnl < 0 and daily_loss >= self.max_daily_loss:
            return False, (
                f"Trading blocked: daily loss limit reached "
                f"({daily_loss:.2%})"
            )

        return True, "Daily-loss check passed"

    def calculate_position_size(
        self,
        account_balance,
        entry_price,
        stop_loss,
        contract_value=1.0,
    ):
        """
        Calculate position size from account risk.

        Formula:

        risk amount =
            account balance × risk percentage

        price risk =
            absolute(entry - stop)

        position size =
            risk amount / price risk
        """

        if account_balance <= 0:
            return 0.0

        if entry_price <= 0:
            return 0.0

        if stop_loss <= 0:
            return 0.0

        price_risk = abs(
            entry_price - stop_loss
        )

        if price_risk <= 0:
            return 0.0

        risk_amount = (
            account_balance
            * self.max_risk_per_trade
        )

        raw_position_size = (
            risk_amount
            / (price_risk * contract_value)
        )

        # Limit position value.
        maximum_value = (
            account_balance
            * self.max_position_value
        )

        maximum_position_size = (
            maximum_value / entry_price
        )

        position_size = min(
            raw_position_size,
            maximum_position_size,
        )

        return max(
            0.0,
            position_size
        )

    def check_signal(
        self,
        df,
        signal,
        account_balance,
        peak_balance,
        daily_pnl,
        starting_daily_balance,
    ):
        """
        Run all currently available risk checks.

        Returns:

            allowed: True/False
            reasons: list of explanations
        """

        reasons = []

        if self.kill_switch:
            return False, [
                "Trading blocked: kill switch is active"
            ]

        data_ok, data_message = (
            self.check_data_quality(df)
        )

        if not data_ok:
            return False, [data_message]

        if signal not in ["LONG", "SHORT"]:
            return False, [
                "No trade: signal is not LONG or SHORT"
            ]

        latest = df.iloc[-1]

        volatility_ok, volatility_message = (
            self.check_volatility(
                latest["volatility_regime"]
            )
        )

        if not volatility_ok:
            return False, [volatility_message]

        drawdown_ok, drawdown_message = (
            self.check_drawdown(
                account_balance,
                peak_balance,
            )
        )

        if not drawdown_ok:
            return False, [drawdown_message]

        daily_ok, daily_message = (
            self.check_daily_loss(
                daily_pnl,
                starting_daily_balance,
            )
        )

        if not daily_ok:
            return False, [daily_message]

        reasons.append(data_message)
        reasons.append(volatility_message)
        reasons.append(drawdown_message)
        reasons.append(daily_message)

        reasons.append(
            "All current risk checks passed"
        )

        return True, reasons