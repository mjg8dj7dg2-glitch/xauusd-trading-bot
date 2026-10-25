from __future__ import annotations

import uuid
from datetime import datetime, timezone

from engines.paper_persistence import PaperPersistence


class PaperTradingSession:
    """
    Coordinates a paper-trading session.

    Responsibilities:
    - Create a persistent session
    - Accept the existing paper-trading report
    - Persist trades
    - Persist equity curve
    - Persist risk events
    - Run the existing paper monitor
    - Persist monitor snapshots
    - Provide session history

    This class does NOT place real trades.
    """

    def __init__(
        self,
        persistence=None,
        monitor=None,
        strategy_name="PAPER_STRATEGY",
        session_id=None,
        metadata=None,
    ):
        self.persistence = (
            persistence
            if persistence is not None
            else PaperPersistence("trading_bot.db")
        )

        self.monitor = monitor
        self.strategy_name = strategy_name

        self.session_id = (
            session_id
            if session_id is not None
            else self._generate_session_id()
        )

        self.metadata = metadata or {}

        self.started = False
        self.finished = False

        self.latest_report = None
        self.latest_monitor_snapshot = None

    @staticmethod
    def _generate_session_id():
        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%d_%H%M%S")

        short_id = uuid.uuid4().hex[:8]

        return f"PAPER_{timestamp}_{short_id}"

    def start(
        self,
        initial_balance=None,
    ):
        if self.started:
            return self.session_id

        self.persistence.create_session(
            session_id=self.session_id,
            strategy_name=self.strategy_name,
            metadata=self.metadata,
            status="RUNNING",
            initial_balance=initial_balance,
        )

        self.started = True
        self.finished = False

        return self.session_id

    def save_report(
        self,
        report,
    ):
        if not isinstance(report, dict):
            raise TypeError(
                "Paper-trading report must be a dictionary."
            )

        if not self.started:
            initial_balance = (
                report
                .get("account", {})
                .get("initial_balance")
            )

            if initial_balance is None:
                initial_balance = (
                    report
                    .get("performance", {})
                    .get("initial_balance")
                )

            self.start(
                initial_balance=initial_balance
            )

        # Update the session's final balance.
        self.persistence.save_paper_report(
            session_id=self.session_id,
            report=report,
        )

        # ------------------------------------------------------------
        # Persist the actual paper-trading records.
        #
        # PaperTradingEngine returns these directly in the report.
        # ------------------------------------------------------------

        trades = report.get("trades", [])

        if trades:
            self.persistence.save_trades(
                session_id=self.session_id,
                trades=trades,
            )

        equity_curve = report.get(
            "equity_curve",
            [],
        )

        if equity_curve:
            self.persistence.save_equity_curve(
                session_id=self.session_id,
                equity_curve=equity_curve,
            )

        risk_events = report.get(
            "risk_events",
            [],
        )

        if risk_events:
            self.persistence.save_risk_events(
                session_id=self.session_id,
                risk_events=risk_events,
            )

        self.latest_report = report

        return self.session_id

    def monitor_report(
        self,
        report=None,
    ):
        if report is None:
            report = self.latest_report

        if report is None:
            raise ValueError(
                "No paper-trading report is available."
            )

        if self.monitor is None:
            return None

        if hasattr(self.monitor, "monitor"):
            snapshot = self.monitor.monitor(
                report
            )

        elif hasattr(self.monitor, "evaluate"):
            snapshot = self.monitor.evaluate(
                report
            )

        elif hasattr(self.monitor, "analyze"):
            snapshot = self.monitor.analyze(
                report
            )

        elif hasattr(self.monitor, "check"):
            snapshot = self.monitor.check(
                report
            )

        elif hasattr(self.monitor, "run"):
            snapshot = self.monitor.run(
                report
            )

        elif callable(self.monitor):
            snapshot = self.monitor(
                report
            )

        else:
            raise TypeError(
                "Monitor must provide monitor(), evaluate(), "
                "analyze(), check(), run(), or be callable."
            )

        if snapshot is None:
            return None

        if not isinstance(snapshot, dict):
            raise TypeError(
                "Paper monitor must return a dictionary."
            )

        self.persistence.save_monitor_snapshot(
            session_id=self.session_id,
            snapshot=snapshot,
        )

        self.latest_monitor_snapshot = snapshot

        return snapshot

    def finish(
        self,
        report=None,
        monitor_snapshot=None,
    ):
        if report is not None:
            self.save_report(report)

        if monitor_snapshot is not None:
            self.persistence.save_monitor_snapshot(
                session_id=self.session_id,
                snapshot=monitor_snapshot,
            )

            self.latest_monitor_snapshot = (
                monitor_snapshot
            )

        elif self.monitor is not None:
            self.monitor_report(
                report=self.latest_report
            )

        final_balance = None

        if self.latest_report is not None:
            final_balance = (
                self.latest_report
                .get("account", {})
                .get("final_balance")
            )

        self.persistence.update_session(
            self.session_id,
            status="FINISHED",
            final_balance=final_balance,
            finished_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )

        self.finished = True

        return self.get_summary()

    def get_session(self):
        return self.persistence.get_session(
            self.session_id
        )

    def get_trades(self):
        return self.persistence.get_session_trades(
            self.session_id
        )

    def get_equity_curve(self):
        return self.persistence.get_session_equity_curve(
            self.session_id
        )

    def get_risk_events(self):
        return self.persistence.get_session_risk_events(
            self.session_id
        )

    def get_monitor_history(
        self,
        limit=100,
    ):
        return self.persistence.get_monitor_history(
            self.session_id,
            limit=limit,
        )

    def get_record_counts(self):
        return self.persistence.count_records(
            self.session_id
        )

    def get_summary(self):
        session = self.get_session()

        return {
            "session_id": self.session_id,
            "strategy_name": self.strategy_name,
            "started": self.started,
            "finished": self.finished,
            "session": session,
            "record_counts": self.get_record_counts(),
            "latest_monitor": (
                self.latest_monitor_snapshot
            ),
        }

    def process_report(
        self,
        report,
        run_monitor=True,
    ):
        self.save_report(report)

        monitor_snapshot = None

        if run_monitor and self.monitor is not None:
            monitor_snapshot = self.monitor_report(
                report=report
            )

        return {
            "session_id": self.session_id,
            "status": report.get(
                "status",
                "COMPLETE",
            ),
            "report": report,
            "monitor": monitor_snapshot,
            "session": self.get_session(),
            "record_counts": self.get_record_counts(),
        }


if __name__ == "__main__":
    session = PaperTradingSession(
        strategy_name="TEST_STRATEGY"
    )

    session.start(
        initial_balance=10000.0
    )

    print(
        "Paper trading session manager initialized."
    )

    print(
        f"Session ID: {session.session_id}"
    )