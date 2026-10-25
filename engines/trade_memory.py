import math
import pandas as pd


class TradeMemory:

    def __init__(
        self,
        minimum_similarity=0.60,
        max_results=10,
    ):
        self.minimum_similarity = (
            minimum_similarity
        )

        self.max_results = max_results

    def _safe_float(self, value):
        """
        Convert a value to float safely.
        """
        try:
            value = float(value)

            if math.isnan(value):
                return None

            return value

        except (TypeError, ValueError):
            return None

    def _numeric_similarity(
        self,
        value_a,
        value_b,
        tolerance,
    ):
        """
        Returns a similarity between 0 and 1.

        1.0 = very similar
        0.0 = very different
        """

        a = self._safe_float(value_a)
        b = self._safe_float(value_b)

        if a is None or b is None:
            return None

        if tolerance <= 0:
            return 1.0 if a == b else 0.0

        difference = abs(a - b)

        similarity = (
            1.0
            - difference / tolerance
        )

        return max(
            0.0,
            min(1.0, similarity),
        )

    def _categorical_similarity(
        self,
        value_a,
        value_b,
    ):
        """
        Compare categorical values.
        """

        if value_a is None or value_b is None:
            return None

        if str(value_a) == str(value_b):
            return 1.0

        return 0.0

    def calculate_similarity(
        self,
        current_trade,
        historical_trade,
    ):
        """
        Calculate similarity between two trades.

        Returns a value between 0 and 1.
        """

        scores = []

        # Direction
        direction_score = (
            self._categorical_similarity(
                current_trade.get("direction"),
                historical_trade.get("direction"),
            )
        )

        if direction_score is not None:
            scores.append(direction_score)

        # Trend regime
        trend_score = (
            self._categorical_similarity(
                current_trade.get(
                    "trend_regime"
                ),
                historical_trade.get(
                    "trend_regime"
                ),
            )
        )

        if trend_score is not None:
            scores.append(trend_score)

        # Volatility regime
        volatility_score = (
            self._categorical_similarity(
                current_trade.get(
                    "volatility_regime"
                ),
                historical_trade.get(
                    "volatility_regime"
                ),
            )
        )

        if volatility_score is not None:
            scores.append(volatility_score)

        # RSI
        rsi_score = self._numeric_similarity(
            current_trade.get("rsi"),
            historical_trade.get("rsi"),
            tolerance=10.0,
        )

        if rsi_score is not None:
            scores.append(rsi_score)

        # ATR
        atr_score = self._numeric_similarity(
            current_trade.get("atr"),
            historical_trade.get("atr"),
            tolerance=2.0,
        )

        if atr_score is not None:
            scores.append(atr_score)

        # EMA
        ema_score = self._numeric_similarity(
            current_trade.get("ema"),
            historical_trade.get("ema"),
            tolerance=10.0,
        )

        if ema_score is not None:
            scores.append(ema_score)

        # SMA
        sma_score = self._numeric_similarity(
            current_trade.get("sma"),
            historical_trade.get("sma"),
            tolerance=10.0,
        )

        if sma_score is not None:
            scores.append(sma_score)

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def find_similar_trades(
        self,
        current_trade,
        historical_trades,
    ):
        """
        Find historical trades similar
        to the current trade.
        """

        matches = []

        for index, trade in enumerate(
            historical_trades
        ):

            similarity = (
                self.calculate_similarity(
                    current_trade,
                    trade,
                )
            )

            if (
                similarity
                >= self.minimum_similarity
            ):

                matches.append(
                    {
                        "index": index,
                        "similarity": similarity,
                        "trade": trade,
                    }
                )

        matches.sort(
            key=lambda item: item[
                "similarity"
            ],
            reverse=True,
        )

        return matches[
            : self.max_results
        ]

    def summarize_similar_trades(
        self,
        similar_trades,
    ):
        """
        Summarize the historical outcomes
        of similar trades.
        """

        if not similar_trades:
            return {
                "similar_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "conclusion": (
                    "No sufficiently similar "
                    "historical trades found."
                ),
            }

        pnl_values = []

        for item in similar_trades:

            pnl = self._safe_float(
                item["trade"].get("pnl")
            )

            if pnl is not None:
                pnl_values.append(pnl)

        if not pnl_values:
            return {
                "similar_trades": len(
                    similar_trades
                ),
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "conclusion": (
                    "Similar trades were found, "
                    "but their outcomes are unavailable."
                ),
            }

        pnl_series = pd.Series(
            pnl_values,
            dtype=float,
        )

        winning_trades = int(
            (pnl_series > 0).sum()
        )

        losing_trades = int(
            (pnl_series < 0).sum()
        )

        win_rate = (
            winning_trades
            / len(pnl_values)
        )

        total_pnl = float(
            pnl_series.sum()
        )

        average_pnl = float(
            pnl_series.mean()
        )

        if average_pnl > 0:
            conclusion = (
                "Similar historical trades "
                "had positive average P&L."
            )

        elif average_pnl < 0:
            conclusion = (
                "Similar historical trades "
                "had negative average P&L."
            )

        else:
            conclusion = (
                "Similar historical trades "
                "had approximately neutral P&L."
            )

        return {
            "similar_trades": len(
                similar_trades
            ),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "average_pnl": average_pnl,
            "conclusion": conclusion,
        }

    def analyze(
        self,
        current_trade,
        historical_trades,
    ):
        """
        Complete trade-memory analysis.
        """

        similar_trades = (
            self.find_similar_trades(
                current_trade,
                historical_trades,
            )
        )

        summary = (
            self.summarize_similar_trades(
                similar_trades
            )
        )

        return {
            "current_trade": current_trade,
            "matches": similar_trades,
            "summary": summary,
        }