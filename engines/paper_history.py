from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


class PaperHistoryAnalyzer:
    """
    Analyze historical paper-trading sessions.

    Repeated executions of the same historical simulation are treated as
    duplicate evidence rather than independent experiments.

    Fingerprints intentionally ignore:
    - session_id
    - trade_id
    - timestamps
    - session-specific metadata

    Fingerprints use stable simulation results such as:
    - strategy name
    - initial balance
    - ordered trade direction
    - prices
    - stops/targets
    - quantity
    - P&L
    - result
    - regime
    - volatility regime
    """

    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = Path(db_path)

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_value(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, float):
            return format(value, ".12g")

        if isinstance(value, int):
            return str(value)

        if isinstance(value, (dict, list, tuple)):
            return json.dumps(
                value,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )

        return str(value)

    @staticmethod
    def _max_drawdown_from_equity(equity_curve):
        if not equity_curve:
            return 0.0

        peak = None
        max_drawdown = 0.0

        for point in equity_curve:
            if isinstance(point, dict):
                value = point.get("equity")

                if value is None:
                    value = point.get("balance")
            else:
                value = point

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            if peak is None or value > peak:
                peak = value

            if peak and peak > 0:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    @staticmethod
    def _calculate_profit_factor(trades):
        gross_profit = 0.0
        gross_loss = 0.0

        for trade in trades:
            pnl = PaperHistoryAnalyzer._safe_float(
                trade.get("pnl")
            )

            if pnl > 0:
                gross_profit += pnl
            elif pnl < 0:
                gross_loss += abs(pnl)

        if gross_loss == 0:
            if gross_profit > 0:
                return float("inf")
            return 0.0

        return gross_profit / gross_loss

    @staticmethod
    def _calculate_losing_streak(trades):
        longest = 0
        current = 0

        for trade in trades:
            pnl = PaperHistoryAnalyzer._safe_float(
                trade.get("pnl")
            )

            if pnl < 0:
                current += 1
                longest = max(longest, current)
            else:
                current = 0

        return longest

    def _get_sessions(self, strategy_name=None, limit=None):
        query = """
            SELECT *
            FROM paper_sessions
        """

        parameters = []

        if strategy_name is not None:
            query += " WHERE strategy_name = ?"
            parameters.append(strategy_name)

        query += """
            ORDER BY COALESCE(finished_at, started_at) DESC
        """

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(int(limit))

        with closing(self._connect()) as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [dict(row) for row in rows]

    def _get_trades(self, session_id):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM paper_trades
                WHERE session_id = ?
                ORDER BY timestamp ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _get_equity_curve(self, session_id):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM paper_equity_curve
                WHERE session_id = ?
                ORDER BY timestamp ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _get_monitor_snapshots(self, session_id):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM paper_monitor_snapshots
                WHERE session_id = ?
                ORDER BY timestamp ASC, id ASC
                """,
                (session_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _session_fingerprint(self, session, trades):
        """
        Create a stable fingerprint for a historical simulation.

        IMPORTANT:
        Generated identifiers and timestamps are deliberately excluded.

        This means two executions of the same historical simulation can
        receive the same fingerprint even when:
        - session_id changes
        - trade_id changes
        - execution timestamp changes
        - session metadata changes
        """

        trade_signature = []

        stable_trade_fields = (
            "direction",
            "entry_price",
            "exit_price",
            "stop_loss",
            "take_profit",
            "quantity",
            "pnl",
            "result",
            "strategy_name",
            "regime",
            "volatility_regime",
        )

        for trade in trades:
            trade_signature.append(
                [
                    self._normalize_value(trade.get(field))
                    for field in stable_trade_fields
                ]
            )

        payload = {
            "strategy_name": self._normalize_value(
                session.get("strategy_name")
            ),
            "initial_balance": self._normalize_value(
                session.get("initial_balance")
            ),
            "trade_count": len(trades),
            "trades": trade_signature,
        }

        raw = json.dumps(
            payload,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    def _analyze_direction(self, trades):
        result = {}

        for direction in ("LONG", "SHORT"):
            subset = [
                trade
                for trade in trades
                if str(
                    trade.get("direction", "")
                ).upper() == direction
            ]

            wins = sum(
                1
                for trade in subset
                if self._safe_float(trade.get("pnl")) > 0
            )

            losses = sum(
                1
                for trade in subset
                if self._safe_float(trade.get("pnl")) < 0
            )

            pnl = sum(
                self._safe_float(trade.get("pnl"))
                for trade in subset
            )

            result[direction] = {
                "trades": len(subset),
                "wins": wins,
                "losses": losses,
                "pnl": pnl,
                "win_rate": (
                    wins / len(subset)
                    if subset
                    else 0.0
                ),
                "profit_factor": (
                    self._calculate_profit_factor(subset)
                ),
            }

        return result

    def _analyze_category(self, trades, field):
        categories = {}

        values = sorted(
            {
                str(trade.get(field) or "UNKNOWN")
                for trade in trades
            }
        )

        for category in values:
            subset = [
                trade
                for trade in trades
                if str(
                    trade.get(field) or "UNKNOWN"
                ) == category
            ]

            wins = sum(
                1
                for trade in subset
                if self._safe_float(trade.get("pnl")) > 0
            )

            losses = sum(
                1
                for trade in subset
                if self._safe_float(trade.get("pnl")) < 0
            )

            pnl = sum(
                self._safe_float(trade.get("pnl"))
                for trade in subset
            )

            categories[category] = {
                "trades": len(subset),
                "wins": wins,
                "losses": losses,
                "pnl": pnl,
                "win_rate": (
                    wins / len(subset)
                    if subset
                    else 0.0
                ),
                "profit_factor": (
                    self._calculate_profit_factor(subset)
                ),
            }

        return categories

    def _analyze_session(self, session):
        session_id = session["session_id"]

        trades = self._get_trades(session_id)
        equity_curve = self._get_equity_curve(session_id)
        monitors = self._get_monitor_snapshots(session_id)

        wins = sum(
            1
            for trade in trades
            if self._safe_float(trade.get("pnl")) > 0
        )

        losses = sum(
            1
            for trade in trades
            if self._safe_float(trade.get("pnl")) < 0
        )

        pnl = sum(
            self._safe_float(trade.get("pnl"))
            for trade in trades
        )

        initial_balance = self._safe_float(
            session.get("initial_balance"),
            0.0,
        )

        final_balance = session.get("final_balance")

        if final_balance is None:
            final_balance = initial_balance + pnl

        final_balance = self._safe_float(
            final_balance
        )

        max_drawdown = self._max_drawdown_from_equity(
            equity_curve
        )

        latest_monitor = (
            monitors[-1]
            if monitors
            else None
        )

        latest_monitor_status = None

        if latest_monitor:
            latest_monitor_status = (
                latest_monitor.get("status")
            )

        return {
            "session_id": session_id,
            "strategy_name": session.get(
                "strategy_name"
            ),
            "status": session.get("status"),
            "started_at": session.get("started_at"),
            "finished_at": session.get("finished_at"),
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "trades": len(trades),
            "wins": wins,
            "losses": losses,
            "pnl": pnl,
            "win_rate": (
                wins / len(trades)
                if trades
                else 0.0
            ),
            "profit_factor": (
                self._calculate_profit_factor(trades)
            ),
            "max_drawdown": max_drawdown,
            "longest_losing_streak": (
                self._calculate_losing_streak(trades)
            ),
            "direction": self._analyze_direction(
                trades
            ),
            "trend_regime": self._analyze_category(
                trades,
                "regime",
            ),
            "volatility_regime": self._analyze_category(
                trades,
                "volatility_regime",
            ),
            "monitor_count": len(monitors),
            "latest_monitor": latest_monitor,
            "latest_monitor_status": (
                latest_monitor_status
            ),
            "fingerprint": self._session_fingerprint(
                session,
                trades,
            ),
        }

    def _aggregate_trades_for_sessions(
        self,
        session_reports,
    ):
        all_trades = []

        for report in session_reports:
            all_trades.extend(
                self._get_trades(
                    report["session_id"]
                )
            )

        return all_trades

    def analyze(self, strategy_name=None, limit=None):
        sessions = self._get_sessions(
            strategy_name=strategy_name,
            limit=limit,
        )

        session_reports = [
            self._analyze_session(session)
            for session in sessions
        ]

        # --------------------------------------------------------------
        # ALL STORED HISTORY
        # --------------------------------------------------------------

        all_trades = self._aggregate_trades_for_sessions(
            session_reports
        )

        aggregate_wins = sum(
            1
            for trade in all_trades
            if self._safe_float(trade.get("pnl")) > 0
        )

        aggregate_losses = sum(
            1
            for trade in all_trades
            if self._safe_float(trade.get("pnl")) < 0
        )

        aggregate_pnl = sum(
            self._safe_float(trade.get("pnl"))
            for trade in all_trades
        )

        aggregate_profit_factor = (
            self._calculate_profit_factor(
                all_trades
            )
        )

        worst_session_dd = max(
            (
                report["max_drawdown"]
                for report in session_reports
            ),
            default=0.0,
        )

        # --------------------------------------------------------------
        # DEDUPLICATION
        # --------------------------------------------------------------

        fingerprints = {}

        for report in session_reports:
            fingerprint = report["fingerprint"]

            fingerprints.setdefault(
                fingerprint,
                [],
            ).append(
                report["session_id"]
            )

        unique_reports = []
        duplicate_reports = []
        empty_reports = []

        seen_fingerprints = set()

        for report in session_reports:
            fingerprint = report["fingerprint"]

            if report["trades"] == 0:
                empty_reports.append(report)

            if fingerprint in seen_fingerprints:
                duplicate_reports.append(report)
            else:
                seen_fingerprints.add(fingerprint)
                unique_reports.append(report)

        unique_trades = (
            self._aggregate_trades_for_sessions(
                unique_reports
            )
        )

        unique_wins = sum(
            1
            for trade in unique_trades
            if self._safe_float(trade.get("pnl")) > 0
        )

        unique_losses = sum(
            1
            for trade in unique_trades
            if self._safe_float(trade.get("pnl")) < 0
        )

        unique_pnl = sum(
            self._safe_float(trade.get("pnl"))
            for trade in unique_trades
        )

        unique_profit_factor = (
            self._calculate_profit_factor(
                unique_trades
            )
        )

        unique_worst_dd = max(
            (
                report["max_drawdown"]
                for report in unique_reports
            ),
            default=0.0,
        )

        # --------------------------------------------------------------
        # HISTORICAL STATUS
        # --------------------------------------------------------------

        active_count = sum(
            1
            for report in session_reports
            if str(
                report.get(
                    "latest_monitor_status"
                )
                or ""
            ).upper() == "ACTIVE"
        )

        review_count = sum(
            1
            for report in session_reports
            if str(
                report.get(
                    "latest_monitor_status"
                )
                or ""
            ).upper() == "REVIEW"
        )

        paused_count = sum(
            1
            for report in session_reports
            if str(
                report.get(
                    "latest_monitor_status"
                )
                or ""
            ).upper() == "PAUSED"
        )

        if (
            not unique_reports
            or all(
                report["trades"] == 0
                for report in unique_reports
            )
        ):
            historical_status = (
                "INSUFFICIENT_DATA"
            )
        elif (
            paused_count > 0
            and paused_count >= active_count
        ):
            historical_status = (
                "PAUSED_HISTORY"
            )
        elif review_count > 0:
            historical_status = (
                "REVIEW_HISTORY"
            )
        else:
            historical_status = "OBSERVATION"

        return {
            "strategy_name": (
                strategy_name or "ALL"
            ),

            # Backward-compatible field used by
            # the existing paper-history tests.
            "sessions_analyzed": len(
                session_reports
            ),

            "sessions": session_reports,

            "aggregate": {
                "sessions": len(
                    session_reports
                ),
                "trades": len(all_trades),
                "wins": aggregate_wins,
                "losses": aggregate_losses,
                "pnl": aggregate_pnl,
                "win_rate": (
                    aggregate_wins / len(all_trades)
                    if all_trades
                    else 0.0
                ),
                "profit_factor": (
                    aggregate_profit_factor
                ),
                "worst_session_drawdown": (
                    worst_session_dd
                ),
            },

            "quality": {
                "stored_sessions": len(
                    session_reports
                ),
                "unique_runs": len(
                    unique_reports
                ),
                "duplicate_runs": len(
                    duplicate_reports
                ),
                "empty_runs": len(
                    empty_reports
                ),
                "duplicate_session_ids": [
                    report["session_id"]
                    for report in duplicate_reports
                ],
                "empty_session_ids": [
                    report["session_id"]
                    for report in empty_reports
                ],
                "fingerprint_groups": {
                    fingerprint: session_ids
                    for fingerprint, session_ids
                    in fingerprints.items()
                },
                "unique_evidence": {
                    "sessions": len(
                        unique_reports
                    ),
                    "trades": len(
                        unique_trades
                    ),
                    "wins": unique_wins,
                    "losses": unique_losses,
                    "pnl": unique_pnl,
                    "win_rate": (
                        unique_wins
                        / len(unique_trades)
                        if unique_trades
                        else 0.0
                    ),
                    "profit_factor": (
                        unique_profit_factor
                    ),
                    "worst_drawdown": (
                        unique_worst_dd
                    ),
                },
            },

            "historical_status": (
                historical_status
            ),
        }

    @staticmethod
    def _format_profit_factor(value):
        if value == float("inf"):
            return "INF"

        return f"{value:.4f}"

    def print_report(self, report):
        print("=" * 88)
        print("PAPER HISTORY ANALYSIS")
        print("=" * 88)

        print(
            f"Strategy           "
            f"{report['strategy_name']}"
        )

        print(
            f"Sessions analyzed  "
            f"{report['sessions_analyzed']}"
        )

        print(
            f"Historical status  "
            f"{report['historical_status']}"
        )

        quality = report["quality"]

        print()
        print("HISTORY QUALITY")

        print(
            f"Stored sessions    "
            f"{quality['stored_sessions']}"
        )

        print(
            f"Unique runs        "
            f"{quality['unique_runs']}"
        )

        print(
            f"Duplicate runs     "
            f"{quality['duplicate_runs']}"
        )

        print(
            f"Empty runs         "
            f"{quality['empty_runs']}"
        )

        print()
        print("AGGREGATE STORED HISTORY")

        aggregate = report["aggregate"]

        print(
            f"P&L               "
            f"{aggregate['pnl']:+.2f}"
        )

        print(
            f"Trades             "
            f"{aggregate['trades']}"
        )

        print(
            f"Wins               "
            f"{aggregate['wins']}"
        )

        print(
            f"Losses             "
            f"{aggregate['losses']}"
        )

        print(
            f"Win rate           "
            f"{aggregate['win_rate']:.2%}"
        )

        print(
            "Profit factor      "
            f"{self._format_profit_factor(aggregate['profit_factor'])}"
        )

        print(
            f"Worst session DD   "
            f"{aggregate['worst_session_drawdown']:.2%}"
        )

        evidence = quality["unique_evidence"]

        print()
        print("UNIQUE EVIDENCE ONLY")
        print(
            "Repeated identical runs are counted once."
        )

        print(
            f"Unique runs        "
            f"{evidence['sessions']}"
        )

        print(
            f"Evidence trades    "
            f"{evidence['trades']}"
        )

        print(
            f"Evidence wins      "
            f"{evidence['wins']}"
        )

        print(
            f"Evidence losses    "
            f"{evidence['losses']}"
        )

        print(
            f"Evidence P&L       "
            f"{evidence['pnl']:+.2f}"
        )

        print(
            f"Evidence win rate  "
            f"{evidence['win_rate']:.2%}"
        )

        print(
            "Evidence PF        "
            f"{self._format_profit_factor(evidence['profit_factor'])}"
        )

        print(
            f"Evidence worst DD  "
            f"{evidence['worst_drawdown']:.2%}"
        )

        print()
        print("SESSION HISTORY")

        for index, session in enumerate(
            report["sessions"],
            start=1,
        ):
            print(
                f"[{index}] "
                f"{session['session_id']} | "
                f"P&L {session['pnl']:+.2f} | "
                f"Trades {session['trades']} | "
                f"Win {session['win_rate']:.2%} | "
                f"PF "
                f"{self._format_profit_factor(session['profit_factor'])} | "
                f"DD {session['max_drawdown']:.2%} | "
                f"Streak "
                f"{session['longest_losing_streak']} | "
                f"FP {session['fingerprint']}"
            )

        print("=" * 88)


def main():
    analyzer = PaperHistoryAnalyzer(
        "trading_bot.db"
    )

    report = analyzer.analyze()

    analyzer.print_report(report)


if __name__ == "__main__":
    main()