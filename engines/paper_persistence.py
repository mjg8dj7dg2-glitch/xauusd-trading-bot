from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


DEFAULT_DB_PATH = Path("trading_bot.db")


class PaperPersistence:
    """
    SQLite persistence layer for paper-trading sessions.

    Supports:
        - PaperTradingSession
        - PaperTradingRunner
        - PaperTradingMonitor
        - Existing trading_bot.db files

    The class intentionally opens a fresh SQLite connection for each
    operation. This avoids Windows SQLite locking problems caused by
    long-lived connections.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

    # ================================================================
    # CONNECTION
    # ================================================================

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    # ================================================================
    # SERIALIZATION
    # ================================================================

    def _serialize_value(self, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, datetime):
            return value.isoformat()

        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass

        if hasattr(value, "item"):
            try:
                return self._serialize_value(value.item())
            except Exception:
                pass

        if isinstance(value, dict):
            return {
                str(key): self._serialize_value(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                self._serialize_value(item)
                for item in value
            ]

        return str(value)

    def _json_safe(
        self,
        value: Any,
        depth: int = 0,
        max_depth: int = 6,
        max_items: int = 100,
    ) -> Any:
        """
        Bound nested JSON structures.

        This is important because trade memory can contain similar trades,
        which themselves may contain memory reports.
        """

        if depth > max_depth:
            return "[TRUNCATED]"

        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, datetime):
            return value.isoformat()

        if hasattr(value, "item"):
            try:
                return self._json_safe(
                    value.item(),
                    depth=depth,
                    max_depth=max_depth,
                    max_items=max_items,
                )
            except Exception:
                pass

        if isinstance(value, dict):
            result = {}

            for index, (key, item) in enumerate(value.items()):
                if index >= max_items:
                    result["__truncated__"] = True
                    break

                result[str(key)] = self._json_safe(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_items=max_items,
                )

            return result

        if isinstance(value, (list, tuple, set)):
            result = []

            for index, item in enumerate(value):
                if index >= max_items:
                    result.append("[TRUNCATED]")
                    break

                result.append(
                    self._json_safe(
                        item,
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_items=max_items,
                    )
                )

            return result

        return str(value)

    def _json_dumps(
        self,
        value: Any,
        max_chars: int = 250_000,
    ) -> str:
        safe_value = self._json_safe(value)

        try:
            text = json.dumps(
                safe_value,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            text = json.dumps(
                str(safe_value),
                ensure_ascii=False,
            )

        if len(text) > max_chars:
            text = json.dumps(
                {
                    "truncated": True,
                    "preview": text[: max_chars - 100],
                },
                ensure_ascii=False,
            )

        return text

    # ================================================================
    # SCHEMA
    # ================================================================

    def _table_columns(
        self,
        connection: sqlite3.Connection,
        table_name: str,
    ) -> set[str]:
        rows = connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {
            row["name"]
            for row in rows
        }

    def _add_missing_columns(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        columns: Dict[str, str],
    ) -> None:
        existing = self._table_columns(
            connection,
            table_name,
        )

        for column_name, definition in columns.items():
            if column_name not in existing:
                connection.execute(
                    f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN {column_name} {definition}
                    """
                )

    def ensure_tables(self) -> None:
        with closing(self._connect()) as connection, connection:

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_sessions (
                    session_id TEXT PRIMARY KEY,
                    strategy_name TEXT,
                    status TEXT,
                    initial_balance REAL,
                    final_balance REAL,
                    started_at TEXT,
                    finished_at TEXT,
                    metadata_json TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    trade_id TEXT,
                    timestamp TEXT,
                    direction TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    quantity REAL,
                    pnl REAL,
                    result TEXT,
                    strategy_name TEXT,
                    regime TEXT,
                    volatility_regime TEXT,
                    memory_summary_json TEXT,
                    metadata_json TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_equity_curve (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT,
                    equity REAL,
                    balance REAL,
                    drawdown REAL,
                    metadata_json TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT,
                    event_type TEXT,
                    allowed INTEGER,
                    reason TEXT,
                    metadata_json TEXT
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_monitor_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT,
                    status TEXT,
                    safe INTEGER,
                    review_required INTEGER,
                    metrics_json TEXT,
                    reasons_json TEXT,
                    warnings_json TEXT,
                    thresholds_json TEXT,
                    metadata_json TEXT
                )
                """
            )

            self._add_missing_columns(
                connection,
                "paper_sessions",
                {
                    "strategy_name": "TEXT",
                    "status": "TEXT",
                    "initial_balance": "REAL",
                    "final_balance": "REAL",
                    "started_at": "TEXT",
                    "finished_at": "TEXT",
                    "metadata_json": "TEXT",
                },
            )

            self._add_missing_columns(
                connection,
                "paper_trades",
                {
                    "trade_id": "TEXT",
                    "timestamp": "TEXT",
                    "direction": "TEXT",
                    "entry_price": "REAL",
                    "exit_price": "REAL",
                    "stop_loss": "REAL",
                    "take_profit": "REAL",
                    "quantity": "REAL",
                    "pnl": "REAL",
                    "result": "TEXT",
                    "strategy_name": "TEXT",
                    "regime": "TEXT",
                    "volatility_regime": "TEXT",
                    "memory_summary_json": "TEXT",
                    "metadata_json": "TEXT",
                },
            )

            self._add_missing_columns(
                connection,
                "paper_equity_curve",
                {
                    "timestamp": "TEXT",
                    "equity": "REAL",
                    "balance": "REAL",
                    "drawdown": "REAL",
                    "metadata_json": "TEXT",
                },
            )

            self._add_missing_columns(
                connection,
                "paper_risk_events",
                {
                    "timestamp": "TEXT",
                    "event_type": "TEXT",
                    "allowed": "INTEGER",
                    "reason": "TEXT",
                    "metadata_json": "TEXT",
                },
            )

            self._add_missing_columns(
                connection,
                "paper_monitor_snapshots",
                {
                    "timestamp": "TEXT",
                    "status": "TEXT",
                    "safe": "INTEGER",
                    "review_required": "INTEGER",
                    "metrics_json": "TEXT",
                    "reasons_json": "TEXT",
                    "warnings_json": "TEXT",
                    "thresholds_json": "TEXT",
                    "metadata_json": "TEXT",
                },
            )

            connection.commit()

    # ================================================================
    # SESSION
    # ================================================================

    def create_session(
        self,
        session_id: str,
        strategy_name: str = "PAPER_STRATEGY",
        initial_balance: Optional[float] = None,
        started_at: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "RUNNING",
        final_balance: Optional[float] = None,
        finished_at: Optional[Any] = None,
    ) -> str:

        self.ensure_tables()

        if started_at is None:
            started_at = datetime.now().astimezone()

        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO paper_sessions (
                    session_id,
                    strategy_name,
                    status,
                    initial_balance,
                    final_balance,
                    started_at,
                    finished_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    strategy_name,
                    status,
                    initial_balance,
                    final_balance,
                    self._serialize_value(started_at),
                    self._serialize_value(finished_at),
                    self._json_dumps(metadata or {}),
                ),
            )

            connection.commit()

        return session_id

    def update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        final_balance: Optional[float] = None,
        finished_at: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:

        self.ensure_tables()

        fields = []
        values = []

        if status is not None:
            fields.append("status = ?")
            values.append(status)

        if final_balance is not None:
            fields.append("final_balance = ?")
            values.append(final_balance)

        if finished_at is not None:
            fields.append("finished_at = ?")
            values.append(
                self._serialize_value(finished_at)
            )

        if metadata is not None:
            fields.append("metadata_json = ?")
            values.append(
                self._json_dumps(metadata)
            )

        if not fields:
            return

        values.append(session_id)

        with closing(self._connect()) as connection, connection:
            connection.execute(
                f"""
                UPDATE paper_sessions
                SET {", ".join(fields)}
                WHERE session_id = ?
                """,
                values,
            )

            connection.commit()

    # ================================================================
    # TRADE COMPACTION
    # ================================================================

    def _compact_trade(
        self,
        trade: Dict[str, Any],
    ) -> Dict[str, Any]:

        memory_summary = trade.get(
            "memory_summary"
        )

        if memory_summary is None:
            memory_report = trade.get(
                "memory_report"
            )

            if isinstance(memory_report, dict):
                memory_summary = {}

                for key in (
                    "similar_trade_count",
                    "similar_trades_count",
                    "losing_pattern_count",
                    "recent_loss_count",
                    "recent_losses",
                    "summary",
                ):
                    if key in memory_report:
                        memory_summary[key] = (
                            memory_report[key]
                        )

        compact = {
            "trade_id": trade.get(
                "trade_id",
                trade.get("id"),
            ),
            "timestamp": trade.get(
                "timestamp",
                trade.get("entry_time"),
            ),
            "direction": trade.get(
                "direction",
                trade.get("side"),
            ),
            "entry_price": trade.get(
                "entry_price"
            ),
            "exit_price": trade.get(
                "exit_price"
            ),
            "stop_loss": trade.get(
                "stop_loss"
            ),
            "take_profit": trade.get(
                "take_profit"
            ),
            "quantity": trade.get(
                "quantity",
                trade.get("size"),
            ),
            "pnl": trade.get(
                "pnl",
                trade.get("profit"),
            ),
            "result": trade.get(
                "result"
            ),
            "strategy_name": trade.get(
                "strategy_name"
            ),
            "regime": trade.get(
                "regime",
                trade.get("trend_regime"),
            ),
            "volatility_regime": trade.get(
                "volatility_regime"
            ),
            "memory_summary": memory_summary,
        }

        metadata = {}

        excluded = {
            "trade_id",
            "id",
            "timestamp",
            "entry_time",
            "direction",
            "side",
            "entry_price",
            "exit_price",
            "stop_loss",
            "take_profit",
            "quantity",
            "size",
            "pnl",
            "profit",
            "result",
            "strategy_name",
            "regime",
            "trend_regime",
            "volatility_regime",
            "memory_report",
            "memory_summary",
        }

        for key, value in trade.items():
            if key not in excluded:
                metadata[key] = value

        compact["metadata"] = metadata

        return compact

    # ================================================================
    # REPORT
    # ================================================================

    def save_paper_report(
        self,
        session_id: str,
        report: Dict[str, Any],
    ) -> None:

        self.ensure_tables()

        account = report.get(
            "account",
            {},
        )

        performance = report.get(
            "performance",
            {},
        )

        final_balance = account.get(
            "final_balance"
        )

        if final_balance is None:
            final_balance = performance.get(
                "final_balance"
            )

        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                UPDATE paper_sessions
                SET final_balance = ?
                WHERE session_id = ?
                """,
                (
                    final_balance,
                    session_id,
                ),
            )

            connection.commit()

    # ================================================================
    # SAVE TRADES
    # ================================================================

    def save_trades(
        self,
        session_id: str,
        trades: Iterable[Dict[str, Any]],
    ) -> int:

        self.ensure_tables()

        rows = []

        for trade in trades:

            compact = self._compact_trade(
                trade
            )

            rows.append(
                (
                    session_id,
                    self._serialize_value(
                        compact.get("trade_id")
                    ),
                    self._serialize_value(
                        compact.get("timestamp")
                    ),
                    self._serialize_value(
                        compact.get("direction")
                    ),
                    compact.get("entry_price"),
                    compact.get("exit_price"),
                    compact.get("stop_loss"),
                    compact.get("take_profit"),
                    compact.get("quantity"),
                    compact.get("pnl"),
                    self._serialize_value(
                        compact.get("result")
                    ),
                    self._serialize_value(
                        compact.get("strategy_name")
                    ),
                    self._serialize_value(
                        compact.get("regime")
                    ),
                    self._serialize_value(
                        compact.get(
                            "volatility_regime"
                        )
                    ),
                    self._json_dumps(
                        compact.get(
                            "memory_summary"
                        )
                    ),
                    self._json_dumps(
                        compact.get(
                            "metadata"
                        )
                    ),
                )
            )

        if not rows:
            return 0

        with closing(self._connect()) as connection, connection:
            connection.executemany(
                """
                INSERT INTO paper_trades (
                    session_id,
                    trade_id,
                    timestamp,
                    direction,
                    entry_price,
                    exit_price,
                    stop_loss,
                    take_profit,
                    quantity,
                    pnl,
                    result,
                    strategy_name,
                    regime,
                    volatility_regime,
                    memory_summary_json,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            connection.commit()

        return len(rows)

    # ================================================================
    # SAVE EQUITY
    # ================================================================

    def save_equity_curve(
        self,
        session_id: str,
        equity_curve: Iterable[Any],
    ) -> int:

        self.ensure_tables()

        rows = []

        for point in equity_curve:

            if isinstance(point, dict):
                timestamp = point.get(
                    "timestamp"
                )

                equity = point.get(
                    "equity"
                )

                balance = point.get(
                    "balance"
                )

                drawdown = point.get(
                    "drawdown"
                )

                metadata = point

            else:
                timestamp = None

                # BacktestEngine returns equity_curve as plain numeric
                # account-balance values. Preserve those values in the
                # numeric equity/balance columns instead of writing NULL.
                try:
                    equity = float(point)
                    balance = equity
                except (TypeError, ValueError):
                    equity = None
                    balance = None

                drawdown = None
                metadata = {
                    "raw_value": point,
                }

            # If a dictionary supplies only balance or only equity, mirror
            # the available numeric value into the other column.
            if isinstance(point, dict):
                if equity is None and balance is not None:
                    try:
                        equity = float(balance)
                    except (TypeError, ValueError):
                        pass

                if balance is None and equity is not None:
                    try:
                        balance = float(equity)
                    except (TypeError, ValueError):
                        pass

            rows.append(
                (
                    session_id,
                    self._serialize_value(
                        timestamp
                    ),
                    equity,
                    balance,
                    drawdown,
                    self._json_dumps(
                        metadata
                    ),
                )
            )

        if not rows:
            return 0

        with closing(self._connect()) as connection, connection:
            connection.executemany(
                """
                INSERT INTO paper_equity_curve (
                    session_id,
                    timestamp,
                    equity,
                    balance,
                    drawdown,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            connection.commit()

        return len(rows)

    # ================================================================
    # SAVE RISK EVENTS
    # ================================================================

    def save_risk_events(
        self,
        session_id: str,
        risk_events: Iterable[Dict[str, Any]],
    ) -> int:

        self.ensure_tables()

        rows = []

        for event in risk_events:

            timestamp = event.get(
                "timestamp"
            )

            if timestamp is None:
                timestamp = (
                    datetime.now()
                    .astimezone()
                )

            rows.append(
                (
                    session_id,
                    self._serialize_value(
                        timestamp
                    ),
                    self._serialize_value(
                        event.get("event_type")
                        or event.get("type")
                        or event.get("action")
                    ),
                    (
                        None
                        if event.get("allowed") is None
                        else int(bool(event.get("allowed")))
                    ),
                    self._serialize_value(
                        event.get("reason")
                        if event.get("reason") is not None
                        else (
                            "; ".join(
                                str(item)
                                for item in event.get("reasons", [])
                            )
                            if isinstance(event.get("reasons"), list)
                            else event.get("reasons")
                        )
                    ),
                    self._json_dumps(
                        event
                    ),
                )
            )

        if not rows:
            return 0

        with closing(self._connect()) as connection, connection:
            connection.executemany(
                """
                INSERT INTO paper_risk_events (
                    session_id,
                    timestamp,
                    event_type,
                    allowed,
                    reason,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            connection.commit()

        return len(rows)

    # ================================================================
    # SAVE MONITOR
    # ================================================================

    def save_monitor_snapshot(
        self,
        session_id: str,
        snapshot: Dict[str, Any],
    ) -> int:

        self.ensure_tables()

        timestamp = snapshot.get(
            "timestamp"
        )

        if timestamp is None:
            timestamp = (
                datetime.now()
                .astimezone()
            )

        status = snapshot.get(
            "status"
        )

        safe = snapshot.get(
            "safe",
            False,
        )

        review_required = snapshot.get(
            "review_required",
            snapshot.get(
                "review",
                False,
            ),
        )

        metrics = snapshot.get(
            "metrics",
            {},
        )

        reasons = snapshot.get(
            "reasons",
            [],
        )

        warnings = snapshot.get(
            "warnings",
            [],
        )

        thresholds = snapshot.get(
            "thresholds",
            {},
        )

        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO paper_monitor_snapshots (
                    session_id,
                    timestamp,
                    status,
                    safe,
                    review_required,
                    metrics_json,
                    reasons_json,
                    warnings_json,
                    thresholds_json,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    self._serialize_value(
                        timestamp
                    ),
                    self._serialize_value(
                        status
                    ),
                    int(bool(safe)),
                    int(
                        bool(
                            review_required
                        )
                    ),
                    self._json_dumps(
                        metrics
                    ),
                    self._json_dumps(
                        reasons
                    ),
                    self._json_dumps(
                        warnings
                    ),
                    self._json_dumps(
                        thresholds
                    ),
                    self._json_dumps(
                        snapshot
                    ),
                ),
            )

            connection.commit()

            return int(
                cursor.lastrowid
            )

    # ================================================================
    # READ SESSION
    # ================================================================

    def get_session(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:

        self.ensure_tables()

        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT *
                FROM paper_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        result = dict(row)

        if result.get(
            "metadata_json"
        ):
            try:
                result["metadata"] = (
                    json.loads(
                        result[
                            "metadata_json"
                        ]
                    )
                )
            except Exception:
                result["metadata"] = {}

        return result

    # ================================================================
    # READ TRADES
    # ================================================================

    def get_trades(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        self.ensure_tables()

        query = """
            SELECT *
            FROM paper_trades
            WHERE session_id = ?
            ORDER BY id ASC
        """

        parameters: list[Any] = [
            session_id
        ]

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(
                int(limit)
            )

        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    # IMPORTANT COMPATIBILITY METHOD
    def get_session_trades(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        return self.get_trades(
            session_id,
            limit=limit,
        )

    # ================================================================
    # READ EQUITY
    # ================================================================

    def get_equity_curve(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        self.ensure_tables()

        query = """
            SELECT *
            FROM paper_equity_curve
            WHERE session_id = ?
            ORDER BY id ASC
        """

        parameters: list[Any] = [
            session_id
        ]

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(
                int(limit)
            )

        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get_session_equity_curve(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        return self.get_equity_curve(
            session_id,
            limit=limit,
        )

    # ================================================================
    # READ RISK EVENTS
    # ================================================================

    def get_risk_events(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        self.ensure_tables()

        query = """
            SELECT *
            FROM paper_risk_events
            WHERE session_id = ?
            ORDER BY id ASC
        """

        parameters: list[Any] = [
            session_id
        ]

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(
                int(limit)
            )

        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get_session_risk_events(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        return self.get_risk_events(
            session_id,
            limit=limit,
        )

    # ================================================================
    # READ MONITOR SNAPSHOTS
    # ================================================================

    def get_monitor_snapshots(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        self.ensure_tables()

        query = """
            SELECT *
            FROM paper_monitor_snapshots
            WHERE session_id = ?
            ORDER BY id ASC
        """

        parameters: list[Any] = [
            session_id
        ]

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(
                int(limit)
            )

        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get_session_monitor_snapshots(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[Dict[str, Any]]:

        return self.get_monitor_snapshots(
            session_id,
            limit=limit,
        )

    # ================================================================
    # COMPATIBILITY ALIASES
    # ================================================================

    def get_trade_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ):
        return self.get_session_trades(
            session_id,
            limit=limit,
        )

    def get_equity_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ):
        return self.get_session_equity_curve(
            session_id,
            limit=limit,
        )

    def get_risk_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ):
        return self.get_session_risk_events(
            session_id,
            limit=limit,
        )

    def get_monitor_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ):
        return self.get_session_monitor_snapshots(
            session_id,
            limit=limit,
        )

    # ================================================================
    # COUNT RECORDS
    # ================================================================

    def count_records(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, int]:

        self.ensure_tables()

        with closing(self._connect()) as connection, connection:

            if session_id is None:

                session_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_sessions
                    """
                ).fetchone()[0]

                trade_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_trades
                    """
                ).fetchone()[0]

                equity_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_equity_curve
                    """
                ).fetchone()[0]

                risk_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_risk_events
                    """
                ).fetchone()[0]

                monitor_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_monitor_snapshots
                    """
                ).fetchone()[0]

            else:

                session_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_sessions
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()[0]

                trade_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_trades
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()[0]

                equity_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_equity_curve
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()[0]

                risk_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_risk_events
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()[0]

                monitor_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM paper_monitor_snapshots
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()[0]

        return {
            # Canonical runner/test keys
            "paper_sessions": int(
                session_count
            ),
            "paper_trades": int(
                trade_count
            ),
            "paper_equity_curve": int(
                equity_count
            ),
            "paper_risk_events": int(
                risk_count
            ),
            "paper_monitor_snapshots": int(
                monitor_count
            ),

            # Compatibility aliases
            "sessions": int(
                session_count
            ),
            "trades": int(
                trade_count
            ),
            "equity_curve": int(
                equity_count
            ),
            "risk_events": int(
                risk_count
            ),
            "monitor_snapshots": int(
                monitor_count
            ),
        }

    def get_record_counts(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, int]:

        return self.count_records(
            session_id=session_id
        )


if __name__ == "__main__":

    persistence = PaperPersistence()

    persistence.ensure_tables()

    counts = persistence.count_records()

    print(
        "Paper persistence tables ready."
    )

    print(
        json.dumps(
            counts,
            indent=2
        )
    )


