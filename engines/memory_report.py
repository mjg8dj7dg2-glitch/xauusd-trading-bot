from engines.trade_memory import TradeMemory
from engines.losing_patterns import LosingPatternDetector


class MemoryReport:

    def __init__(
        self,
        minimum_similarity=0.60,
        max_similar_trades=10,
        minimum_losses=3,
        minimum_occurrences=2,
        minimum_percentage=0.50,
    ):
        self.trade_memory = TradeMemory(
            minimum_similarity=minimum_similarity,
            max_results=max_similar_trades,
        )

        self.losing_pattern_detector = LosingPatternDetector(
            minimum_losses=minimum_losses,
            minimum_occurrences=minimum_occurrences,
            minimum_percentage=minimum_percentage,
        )

    def build_report(
        self,
        current_trade,
        historical_trades,
        recent_count=10,
    ):
        """
        Combine similar-trade analysis with
        recurring losing-pattern analysis.
        """

        similar_trade_report = self.trade_memory.analyze(
            current_trade=current_trade,
            historical_trades=historical_trades,
        )

        losing_pattern_report = (
            self.losing_pattern_detector.analyze(
                historical_trades
            )
        )

        recent_loss_report = (
            self.losing_pattern_detector.analyze_recent_losses(
                historical_trades,
                recent_count=recent_count,
            )
        )

        return {
            "similar_trades": similar_trade_report,
            "losing_patterns": losing_pattern_report,
            "recent_losing_patterns": recent_loss_report,
        }

    def summarize(
        self,
        report,
    ):
        """
        Create a simple summary suitable for
        the dashboard or backtest output.
        """

        similar_summary = report[
            "similar_trades"
        ]["summary"]

        losing_patterns = report[
            "losing_patterns"
        ]["patterns"]

        recent_patterns = report[
            "recent_losing_patterns"
        ]["patterns"]

        return {
            "similar_trade_count": (
                similar_summary["similar_trades"]
            ),
            "similar_trade_win_rate": (
                similar_summary["win_rate"]
            ),
            "similar_trade_average_pnl": (
                similar_summary["average_pnl"]
            ),
            "losing_pattern_count": (
                len(losing_patterns)
            ),
            "recent_losing_pattern_count": (
                len(recent_patterns)
            ),
        }