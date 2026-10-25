from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


# =============================================================================
# CONFIG
# =============================================================================

DB_PATH = Path("trading_bot.db")

st.set_page_config(
    page_title="V7 Paper Trading Dashboard",
    page_icon="📊",
    layout="wide",
)


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def connect_db() -> sqlite3.Connection:
    return sqlite3.connect(f"{DB_PATH.resolve().as_uri()}?mode=ro", uri=True)


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def read_table(table_name: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = connect_db()

    try:
        if not table_exists(conn, table_name):
            return pd.DataFrame()

        df = pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            conn,
        )

        # Duplicate SQLite/query column names can produce DataFrame
        # columns with the same name. Keep the first copy.
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated()].copy()

        return df

    finally:
        conn.close()


# =============================================================================
# SAFE VALUE HELPERS
# =============================================================================

def is_missing(value: Any) -> bool:
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def safe_float(value: Any, default: float = 0.0) -> float:
    if is_missing(value):
        return default

    try:
        value = float(value)

        if not math.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    if is_missing(value):
        return default

    try:
        return int(float(value))

    except (TypeError, ValueError):
        return default


def safe_text(value: Any, default: str = "") -> str:
    if is_missing(value):
        return default

    return str(value)


def first_value(row: pd.Series, keys: list[str], default: Any = None) -> Any:
    for key in keys:
        if key in row.index:
            value = row[key]

            if not is_missing(value):
                return value

    return default


def parse_json(value: Any) -> dict:
    if isinstance(value, dict):
        return value

    if is_missing(value):
        return {}

    try:
        parsed = json.loads(str(value))

        if isinstance(parsed, dict):
            return parsed

    except Exception:
        pass

    return {}


# =============================================================================
# TRADE METRICS
# =============================================================================

def calculate_trade_metrics(
    trades: pd.DataFrame,
    initial_balance: float = 10000.0,
) -> dict[str, Any]:

    if trades.empty:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
        }

    work = trades.copy()

    pnl_column = None

    for column in (
        "pnl",
        "profit",
        "profit_loss",
        "realized_pnl",
    ):
        if column in work.columns:
            pnl_column = column
            break

    if pnl_column is None:
        work["__pnl"] = 0.0
        pnl_column = "__pnl"

    work["__pnl"] = pd.to_numeric(
        work[pnl_column],
        errors="coerce",
    ).fillna(0.0)

    total_trades = len(work)

    winning = work[work["__pnl"] > 0]["__pnl"]
    losing = work[work["__pnl"] < 0]["__pnl"]

    winning_trades = len(winning)
    losing_trades = len(losing)

    total_pnl = float(work["__pnl"].sum())

    gross_profit = float(winning.sum())
    gross_loss = abs(float(losing.sum()))

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    win_rate = (
        winning_trades / total_trades
        if total_trades
        else 0.0
    )

    equity = initial_balance + work["__pnl"].cumsum()

    peak = equity.cummax()

    drawdown = (peak - equity) / peak.replace(
        0,
        pd.NA,
    )

    max_drawdown = safe_float(
        drawdown.max(),
        0.0,
    )

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "max_drawdown": max_drawdown,
    }


# =============================================================================
# SESSION PROCESSING
# =============================================================================

def derive_session_metrics(
    sessions: pd.DataFrame,
    trades: pd.DataFrame,
) -> pd.DataFrame:

    if sessions.empty and trades.empty:
        return pd.DataFrame()

    rows = []

    session_ids = set()

    if not sessions.empty and "session_id" in sessions.columns:
        session_ids.update(
            sessions["session_id"]
            .dropna()
            .astype(str)
            .tolist()
        )

    if not trades.empty and "session_id" in trades.columns:
        session_ids.update(
            trades["session_id"]
            .dropna()
            .astype(str)
            .tolist()
        )

    for session_id in sorted(session_ids):

        session_row = pd.Series(dtype=object)

        if (
            not sessions.empty
            and "session_id" in sessions.columns
        ):
            matches = sessions[
                sessions["session_id"].astype(str)
                == str(session_id)
            ]

            if not matches.empty:
                session_row = matches.iloc[-1]

        if not trades.empty and "session_id" in trades.columns:
            session_trades = trades[
                trades["session_id"].astype(str)
                == str(session_id)
            ].copy()
        else:
            session_trades = pd.DataFrame()

        initial_balance = safe_float(
            first_value(
                session_row,
                ["initial_balance"],
                10000.0,
            ),
            10000.0,
        )

        metrics = calculate_trade_metrics(
            session_trades,
            initial_balance=initial_balance,
        )

        session_pnl = first_value(
            session_row,
            ["total_pnl"],
            None,
        )

        if is_missing(session_pnl):
            session_pnl = metrics["total_pnl"]

        max_dd = first_value(
            session_row,
            ["max_drawdown"],
            None,
        )

        if is_missing(max_dd):
            max_dd = metrics["max_drawdown"]

        total_trades = first_value(
            session_row,
            ["total_trades"],
            None,
        )

        if is_missing(total_trades):
            total_trades = metrics["total_trades"]

        wins = first_value(
            session_row,
            ["winning_trades"],
            None,
        )

        if is_missing(wins):
            wins = metrics["winning_trades"]

        losses = first_value(
            session_row,
            ["losing_trades"],
            None,
        )

        if is_missing(losses):
            losses = metrics["losing_trades"]

        win_rate = first_value(
            session_row,
            ["win_rate"],
            None,
        )

        if is_missing(win_rate):
            win_rate = metrics["win_rate"]

        profit_factor = first_value(
            session_row,
            ["profit_factor"],
            None,
        )

        if is_missing(profit_factor):
            profit_factor = metrics["profit_factor"]

        started_at = first_value(
            session_row,
            ["started_at", "created_at"],
            "",
        )

        status = first_value(
            session_row,
            ["status"],
            "",
        )

        strategy_name = first_value(
            session_row,
            ["strategy_name"],
            "",
        )

        rows.append(
            {
                "session_id": session_id,
                "strategy_name": safe_text(strategy_name),
                "started_at": safe_text(started_at),
                "status": safe_text(status),
                "total_trades": safe_int(total_trades),
                "winning_trades": safe_int(wins),
                "losing_trades": safe_int(losses),
                "win_rate": safe_float(win_rate),
                "profit_factor": safe_float(profit_factor),
                "total_pnl": safe_float(session_pnl),
                "max_drawdown": safe_float(max_dd),
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# STABLE SESSION FINGERPRINT
# =============================================================================

def session_fingerprint(row: pd.Series) -> tuple:
    """
    Stable fingerprint intentionally ignores:
        - session_id
        - timestamps
        - created_at
        - finished_at

    This helps remove duplicate simulations of the same result.
    """

    return (
        safe_text(row.get("strategy_name")),
        safe_int(row.get("total_trades")),
        safe_int(row.get("winning_trades")),
        safe_int(row.get("losing_trades")),
        round(safe_float(row.get("win_rate")), 8),
        round(safe_float(row.get("profit_factor")), 8),
        round(safe_float(row.get("total_pnl")), 8),
        round(safe_float(row.get("max_drawdown")), 8),
    )


def deduplicate_sessions(
    session_metrics: pd.DataFrame,
) -> pd.DataFrame:

    if session_metrics.empty:
        return session_metrics.copy()

    work = session_metrics.copy()

    work["__fingerprint"] = work.apply(
        session_fingerprint,
        axis=1,
    )

    # Keep the latest stored instance of a stable result.
    work = work.drop_duplicates(
        subset="__fingerprint",
        keep="last",
    )

    return work.drop(
        columns=["__fingerprint"],
        errors="ignore",
    ).reset_index(drop=True)


# =============================================================================
# RISK EVENT ANALYSIS
# =============================================================================

def classify_risk_event(row: pd.Series) -> str:
    """
    Classify a risk event only from explicit persisted evidence.

    Structured event evidence takes precedence over the legacy/direct
    'allowed' column because the current database contains rows where
    allowed=0 while the stored event action is ENTRY_ALLOWED.
    """

    # Structured JSON evidence is authoritative when it contains an
    # explicit risk action or allowed/blocked decision.
    for key in (
        "metadata_json",
        "risk_json",
        "event_json",
        "metadata",
    ):
        if key not in row.index:
            continue

        payload = parse_json(row[key])

        if not payload:
            continue

        # Explicit action evidence.
        action = payload.get("action")

        if action is not None:
            action_text = str(action).strip().upper()

            if action_text in {
                "ENTRY_ALLOWED",
                "ALLOWED",
                "APPROVED",
            }:
                return "ALLOWED"

            if action_text in {
                "ENTRY_BLOCKED",
                "BLOCKED",
                "DENIED",
            }:
                return "BLOCKED"

        # Explicit allowed evidence inside JSON.
        if "allowed" in payload:
            value = payload["allowed"]

            if isinstance(value, bool):
                return "ALLOWED" if value else "BLOCKED"

            text = str(value).strip().upper()

            if text in {
                "1",
                "TRUE",
                "YES",
                "ALLOWED",
                "PASS",
            }:
                return "ALLOWED"

            if text in {
                "0",
                "FALSE",
                "NO",
                "BLOCKED",
                "DENIED",
            }:
                return "BLOCKED"

    # Direct database field.
    if "allowed" in row.index:
        value = row["allowed"]

        if not is_missing(value):
            if isinstance(value, bool):
                return "ALLOWED" if value else "BLOCKED"

            text = str(value).strip().upper()

            if text in {
                "1",
                "TRUE",
                "YES",
                "ALLOWED",
                "PASS",
            }:
                return "ALLOWED"

            if text in {
                "0",
                "FALSE",
                "NO",
                "BLOCKED",
                "DENIED",
            }:
                return "BLOCKED"

    # Top-level textual evidence.
    text_parts = []

    for key in (
        "event_type",
        "severity",
        "message",
        "action",
        "reason",
    ):
        if key in row.index and not is_missing(row[key]):
            text_parts.append(str(row[key]))

    combined = " ".join(text_parts).upper()

    if "BLOCKED" in combined or "DENIED" in combined:
        return "BLOCKED"

    if "ALLOWED" in combined or "APPROVED" in combined:
        return "ALLOWED"

    return "UNKNOWN"


def analyze_risk_events(
    risk_events: pd.DataFrame,
    selected_session_id: str | None = None,
) -> pd.DataFrame:

    if risk_events.empty:
        return pd.DataFrame(
            columns=[
                "session_id",
                "classification",
                "event_type",
                "severity",
                "message",
                "timestamp",
            ]
        )

    work = risk_events.copy()

    if "session_id" not in work.columns:
        work["session_id"] = ""

    work["classification"] = work.apply(
        classify_risk_event,
        axis=1,
    )

    if selected_session_id is not None:
        work = work[
            work["session_id"].astype(str)
            == str(selected_session_id)
        ].copy()

    return work


# =============================================================================
# SIGNAL ANALYSIS
# =============================================================================

def analyze_signals(
    signals: pd.DataFrame,
    selected_session_id: str | None = None,
) -> pd.DataFrame:

    if signals.empty:
        return pd.DataFrame()

    work = signals.copy()

    # Signals do not necessarily belong to a paper session.
    # Therefore we only filter them if an explicit session_id exists.
    if (
        selected_session_id is not None
        and "session_id" in work.columns
    ):
        work = work[
            work["session_id"].astype(str)
            == str(selected_session_id)
        ].copy()

    return work


# =============================================================================
# STABILITY ANALYSIS
# =============================================================================

def build_stability_summary(
    unique_sessions: pd.DataFrame,
) -> dict[str, Any]:

    if unique_sessions.empty:
        return {
            "session_count": 0,
            "total_trades": 0,
            "total_pnl": 0.0,
            "positive_sessions": 0,
            "positive_ratio": 0.0,
            "average_pnl": 0.0,
            "median_pnl": 0.0,
            "worst_drawdown": 0.0,
            "best_session": None,
            "worst_session": None,
        }

    pnl = pd.to_numeric(
        unique_sessions["total_pnl"],
        errors="coerce",
    ).fillna(0.0)

    dd = pd.to_numeric(
        unique_sessions["max_drawdown"],
        errors="coerce",
    ).fillna(0.0)

    positive = int((pnl > 0).sum())
    session_count = len(unique_sessions)

    best_idx = pnl.idxmax()
    worst_idx = pnl.idxmin()

    return {
        "session_count": session_count,
        "total_trades": int(
            unique_sessions["total_trades"].sum()
        ),
        "total_pnl": float(pnl.sum()),
        "positive_sessions": positive,
        "positive_ratio": (
            positive / session_count
            if session_count
            else 0.0
        ),
        "average_pnl": float(pnl.mean()),
        "median_pnl": float(pnl.median()),
        "worst_drawdown": float(dd.max()),
        "best_session": unique_sessions.loc[best_idx],
        "worst_session": unique_sessions.loc[worst_idx],
    }


def leave_one_out(
    unique_sessions: pd.DataFrame,
) -> pd.DataFrame:

    if len(unique_sessions) < 2:
        return pd.DataFrame()

    rows = []

    for index in unique_sessions.index:

        remaining = unique_sessions.drop(index)

        pnl = pd.to_numeric(
            remaining["total_pnl"],
            errors="coerce",
        ).fillna(0.0)

        dd = pd.to_numeric(
            remaining["max_drawdown"],
            errors="coerce",
        ).fillna(0.0)

        positive = int((pnl > 0).sum())

        rows.append(
            {
                "Removed session": safe_text(
                    unique_sessions.loc[index, "session_id"]
                ),
                "Remaining sessions": len(remaining),
                "Trades": int(
                    remaining["total_trades"].sum()
                ),
                "P&L": float(pnl.sum()),
                "Positive sessions": positive,
                "Positive ratio": (
                    positive / len(remaining)
                    if len(remaining)
                    else 0.0
                ),
                "Worst DD": float(dd.max()),
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# PAGE HEADER
# =============================================================================

st.title("📊 V7 Paper Trading Dashboard")

st.caption(
    "XAUUSD V7 — analysis, paper trading, stability and risk monitoring"
)

st.warning(
    "PAPER / ANALYSIS ONLY — Live trading authorization: NO"
)


# =============================================================================
# LOAD DATA
# =============================================================================

sessions_df = read_table("paper_sessions")
trades_df = read_table("paper_trades")
risk_df = read_table("paper_risk_events")
signals_df = read_table("signals")
monitor_df = read_table("paper_monitor_snapshots")


if (
    sessions_df.empty
    and trades_df.empty
    and risk_df.empty
):
    st.error(
        "No paper-trading data was found in trading_bot.db."
    )
    st.stop()


# =============================================================================
# SESSION METRICS
# =============================================================================

session_metrics = derive_session_metrics(
    sessions_df,
    trades_df,
)

unique_sessions = deduplicate_sessions(
    session_metrics
)

stability = build_stability_summary(
    unique_sessions
)


# =============================================================================
# OVERALL EVIDENCE
# =============================================================================

st.header("Overall V7 Evidence")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Unique Sessions",
    stability["session_count"],
)

c2.metric(
    "Unique Trades",
    stability["total_trades"],
)

if stability["session_count"]:

    all_trades = int(stability["total_trades"])

    all_wins = int(
        unique_sessions["winning_trades"].sum()
    )

    overall_win_rate = (
        all_wins / all_trades
        if all_trades
        else 0.0
    )

else:
    overall_win_rate = 0.0

c3.metric(
    "Win Rate",
    f"{overall_win_rate:.2%}",
)

gross_profit = 0.0
gross_loss = 0.0

if not trades_df.empty and "pnl" in trades_df.columns:

    all_pnl = pd.to_numeric(
        trades_df["pnl"],
        errors="coerce",
    ).fillna(0.0)

    gross_profit = float(
        all_pnl[all_pnl > 0].sum()
    )

    gross_loss = abs(
        float(
            all_pnl[all_pnl < 0].sum()
        )
    )

if gross_loss > 0:
    overall_pf = gross_profit / gross_loss
else:
    overall_pf = (
        float("inf")
        if gross_profit > 0
        else 0.0
    )

c4.metric(
    "Profit Factor",
    (
        f"{overall_pf:.4f}"
        if math.isfinite(overall_pf)
        else "∞"
    ),
)

c5.metric(
    "Aggregate P&L",
    f"${stability['total_pnl']:,.2f}",
)


c6, c7, c8 = st.columns(3)

c6.metric(
    "Positive Sessions",
    f"{stability['positive_sessions']}/{stability['session_count']}",
)

c7.metric(
    "Positive Session Ratio",
    f"{stability['positive_ratio']:.2%}",
)

c8.metric(
    "Worst Session DD",
    f"{stability['worst_drawdown']:.2%}",
)


# =============================================================================
# DASHBOARD STATUS
# =============================================================================

st.header("Dashboard Status")

if (
    stability["session_count"] >= 4
    and stability["positive_ratio"] >= 0.75
):
    dashboard_status = "PAPER / STABILITY-VALIDATED"
else:
    dashboard_status = "PAPER / MORE OBSERVATION NEEDED"

d1, d2, d3 = st.columns(3)

d1.metric(
    "V7 Evidence Status",
    dashboard_status,
)

d2.metric(
    "Live Authorization",
    "NO",
)

d3.metric(
    "Analysis Mode",
    "PAPER ONLY",
)


st.info(
    "Stability validation is a dashboard evidence classification. "
    "It does not promote V7 to active or live trading."
)


# =============================================================================
# SESSION SELECTOR
# =============================================================================

st.header("Selected Paper Session")

if unique_sessions.empty:
    st.warning("No completed paper sessions available.")
    st.stop()

session_options = unique_sessions[
    "session_id"
].astype(str).tolist()

selected_session_id = st.selectbox(
    "Choose a paper session",
    session_options,
    index=len(session_options) - 1,
)

selected = unique_sessions[
    unique_sessions["session_id"].astype(str)
    == str(selected_session_id)
].iloc[0]


selected_trades = trades_df.copy()

if (
    not selected_trades.empty
    and "session_id" in selected_trades.columns
):
    selected_trades = selected_trades[
        selected_trades["session_id"].astype(str)
        == str(selected_session_id)
    ].copy()
else:
    selected_trades = pd.DataFrame()


selected_metrics = calculate_trade_metrics(
    selected_trades,
    initial_balance=10000.0,
)


selected_trade_count = selected_metrics[
    "total_trades"
]

selected_win_rate = selected_metrics[
    "win_rate"
]

selected_pf = selected_metrics[
    "profit_factor"
]

selected_pnl = selected_metrics[
    "total_pnl"
]

selected_dd = selected_metrics[
    "max_drawdown"
]


if selected_trade_count < 10:
    selected_health = "INSUFFICIENT_DATA"
elif selected_trade_count >= 20 and selected_win_rate >= 0.50:
    selected_health = "STABLE_OBSERVATION"
else:
    selected_health = "OBSERVATION"


s1, s2, s3, s4, s5, s6 = st.columns(6)

s1.metric(
    "Health",
    selected_health,
)

s2.metric(
    "Trades",
    selected_trade_count,
)

s3.metric(
    "Win Rate",
    f"{selected_win_rate:.2%}",
)

s4.metric(
    "Profit Factor",
    (
        f"{selected_pf:.4f}"
        if math.isfinite(selected_pf)
        else "∞"
    ),
)

s5.metric(
    "P&L",
    f"${selected_pnl:,.2f}",
)

s6.metric(
    "Max Drawdown",
    f"{selected_dd:.2%}",
)


# =============================================================================
# SESSION DETAILS
# =============================================================================

st.subheader("Selected Session Details")

d1, d2, d3, d4 = st.columns(4)

d1.metric(
    "Wins",
    selected_metrics["winning_trades"],
)

d2.metric(
    "Losses",
    selected_metrics["losing_trades"],
)

d3.metric(
    "Average Trade",
    (
        f"${selected_pnl / selected_trade_count:,.2f}"
        if selected_trade_count
        else "$0.00"
    ),
)

d4.metric(
    "Session ID",
    selected_session_id,
)


# =============================================================================
# EQUITY / TRADE CHART
# =============================================================================

if (
    not selected_trades.empty
    and "pnl" in selected_trades.columns
):

    chart_df = selected_trades.copy()

    chart_df["pnl"] = pd.to_numeric(
        chart_df["pnl"],
        errors="coerce",
    ).fillna(0.0)

    chart_df["equity"] = (
        10000.0
        + chart_df["pnl"].cumsum()
    )

    chart_df["trade_number"] = range(
        1,
        len(chart_df) + 1,
    )

    fig = px.line(
        chart_df,
        x="trade_number",
        y="equity",
        markers=True,
        title="Selected Session Equity Curve",
    )

    fig.update_layout(
        xaxis_title="Trade",
        yaxis_title="Equity",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )


# =============================================================================
# RISK CHECK BREAKDOWN
# =============================================================================

st.header("Risk Check Breakdown")

selected_risk = analyze_risk_events(
    risk_df,
    selected_session_id=selected_session_id,
)

risk_total = len(selected_risk)

if risk_total:

    allowed_count = int(
        (
            selected_risk["classification"]
            == "ALLOWED"
        ).sum()
    )

    blocked_count = int(
        (
            selected_risk["classification"]
            == "BLOCKED"
        ).sum()
    )

    unknown_count = int(
        (
            selected_risk["classification"]
            == "UNKNOWN"
        ).sum()
    )

else:
    allowed_count = 0
    blocked_count = 0
    unknown_count = 0


r1, r2, r3, r4 = st.columns(4)

r1.metric(
    "Persisted Risk Events",
    risk_total,
)

r2.metric(
    "Allowed",
    allowed_count,
)

r3.metric(
    "Blocked",
    blocked_count,
)

r4.metric(
    "Unknown / Unresolved",
    unknown_count,
)


if risk_total:

    if unknown_count == risk_total:
        st.info(
            "The database contains risk-event records, but their "
            "allowed/blocked result is not reliably persisted in the "
            "available fields. The dashboard deliberately reports these "
            "as UNKNOWN rather than guessing."
        )

    risk_display_columns = [
        column
        for column in (
            "timestamp",
            "event_type",
            "severity",
            "classification",
            "message",
            "action",
            "reason",
        )
        if column in selected_risk.columns
    ]

    if risk_display_columns:
        st.dataframe(
            selected_risk[
                risk_display_columns
            ],
            width="stretch",
            hide_index=True,
        )

else:
    st.info(
        "No persisted risk events were found for this session."
    )


# =============================================================================
# SIGNALS VS EXECUTED TRADES
# =============================================================================

st.header("Signal → Trade Flow")

signal_count = 0

if not signals_df.empty:
    signal_count = len(
        analyze_signals(
            signals_df,
            selected_session_id,
        )
    )

executed_count = selected_trade_count

flow1, flow2, flow3 = st.columns(3)

flow1.metric(
    "Persisted Strategy Signals",
    signal_count,
)

flow2.metric(
    "Executed Paper Trades",
    executed_count,
)

flow3.metric(
    "Risk Events",
    risk_total,
)

st.caption(
    "A difference between signals and executed trades is not automatically "
    "a risk block. Strategy filters, duplicate prevention, market conditions, "
    "or other pipeline rules can also account for the difference."
)


# =============================================================================
# SESSION STABILITY
# =============================================================================

st.header("Session Stability")

a1, a2, a3, a4 = st.columns(4)

a1.metric(
    "Average Session P&L",
    f"${stability['average_pnl']:,.2f}",
)

a2.metric(
    "Median Session P&L",
    f"${stability['median_pnl']:,.2f}",
)

a3.metric(
    "Positive Sessions",
    f"{stability['positive_sessions']}/{stability['session_count']}",
)

a4.metric(
    "Worst DD",
    f"{stability['worst_drawdown']:.2%}",
)


if stability["best_session"] is not None:

    best = stability["best_session"]
    worst = stability["worst_session"]

    b1, b2 = st.columns(2)

    with b1:
        st.success(
            "Best Session\n\n"
            f"Session: {safe_text(best['session_id'])}\n\n"
            f"P&L: ${safe_float(best['total_pnl']):,.2f}\n\n"
            f"Trades: {safe_int(best['total_trades'])}\n\n"
            f"Win rate: {safe_float(best['win_rate']):.2%}"
        )

    with b2:
        st.warning(
            "Worst Session\n\n"
            f"Session: {safe_text(worst['session_id'])}\n\n"
            f"P&L: ${safe_float(worst['total_pnl']):,.2f}\n\n"
            f"Trades: {safe_int(worst['total_trades'])}\n\n"
            f"Max DD: {safe_float(worst['max_drawdown']):.2%}"
        )


# =============================================================================
# SESSION TABLE
# =============================================================================

st.subheader("Unique Session Evidence")

session_table = unique_sessions.copy()

session_table["Win Rate"] = (
    session_table["win_rate"]
    .map(lambda x: f"{safe_float(x):.2%}")
)

session_table["Profit Factor"] = (
    session_table["profit_factor"]
    .map(
        lambda x:
        f"{safe_float(x):.4f}"
        if math.isfinite(safe_float(x))
        else "∞"
    )
)

session_table["P&L"] = (
    session_table["total_pnl"]
    .map(lambda x: f"${safe_float(x):,.2f}")
)

session_table["Max DD"] = (
    session_table["max_drawdown"]
    .map(lambda x: f"{safe_float(x):.2%}")
)

session_table["Positive"] = (
    session_table["total_pnl"]
    .map(
        lambda x:
        "YES"
        if safe_float(x) > 0
        else "NO"
    )
)

display_columns = [
    column
    for column in (
        "session_id",
        "strategy_name",
        "total_trades",
        "winning_trades",
        "losing_trades",
        "Win Rate",
        "Profit Factor",
        "P&L",
        "Max DD",
        "Positive",
        "started_at",
    )
    if column in session_table.columns
]

st.dataframe(
    session_table[display_columns],
    width="stretch",
    hide_index=True,
)


# =============================================================================
# SESSION P&L CHART
# =============================================================================

if not unique_sessions.empty:

    plot_sessions = unique_sessions.copy()

    plot_sessions["Session"] = (
        plot_sessions["session_id"].astype(str)
    )

    plot_sessions["P&L"] = pd.to_numeric(
        plot_sessions["total_pnl"],
        errors="coerce",
    ).fillna(0.0)

    fig = px.bar(
        plot_sessions,
        x="Session",
        y="P&L",
        title="P&L by Unique Paper Session",
    )

    fig.update_layout(
        xaxis_title="Session",
        yaxis_title="P&L ($)",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )


# =============================================================================
# LEAVE-ONE-OUT ANALYSIS
# =============================================================================

st.header("Leave-One-Session-Out Stability")

loo = leave_one_out(
    unique_sessions
)

if loo.empty:

    st.info(
        "At least two unique sessions are required for "
        "leave-one-session-out analysis."
    )

else:

    loo_display = loo.copy()

    loo_display["P&L"] = loo_display[
        "P&L"
    ].map(
        lambda x: f"${safe_float(x):,.2f}"
    )

    loo_display["Positive ratio"] = loo_display[
        "Positive ratio"
    ].map(
        lambda x: f"{safe_float(x):.2%}"
    )

    loo_display["Worst DD"] = loo_display[
        "Worst DD"
    ].map(
        lambda x: f"{safe_float(x):.2%}"
    )

    st.dataframe(
        loo_display,
        width="stretch",
        hide_index=True,
    )

    min_loo_pnl = float(
        pd.to_numeric(
            loo["P&L"],
            errors="coerce",
        ).min()
    )

    min_loo_ratio = float(
        pd.to_numeric(
            loo["Positive ratio"],
            errors="coerce",
        ).min()
    )

    if (
        min_loo_pnl > 0
        and min_loo_ratio >= 0.75
    ):
        st.success(
            "Leave-one-session-out evidence remains positive "
            "after removing every individual session."
        )
    else:
        st.warning(
            "Removing at least one session materially weakens "
            "the evidence. More independent paper observations "
            "are appropriate before considering any promotion."
        )


# =============================================================================
# MONITOR SNAPSHOT
# =============================================================================

st.header("Latest Paper Monitor")

if not monitor_df.empty:

    monitor_work = monitor_df.copy()

    if "session_id" in monitor_work.columns:
        monitor_work = monitor_work[
            monitor_work["session_id"].astype(str)
            == str(selected_session_id)
        ].copy()

    if not monitor_work.empty:

        latest_monitor = monitor_work.iloc[-1]

        status = first_value(
            latest_monitor,
            ["status"],
            "UNKNOWN",
        )

        safe_value = first_value(
            latest_monitor,
            ["safe"],
            None,
        )

        review_required = first_value(
            latest_monitor,
            [
                "review_required",
                "needs_review",
            ],
            None,
        )

        m1, m2, m3 = st.columns(3)

        m1.metric(
            "Monitor Status",
            safe_text(status, "UNKNOWN"),
        )

        m2.metric(
            "Safe",
            (
                safe_text(safe_value)
                if not is_missing(safe_value)
                else "UNKNOWN"
            ),
        )

        m3.metric(
            "Review Required",
            (
                safe_text(review_required)
                if not is_missing(review_required)
                else "UNKNOWN"
            ),
        )

    else:
        st.info(
            "No monitor snapshot is available for the selected session."
        )

else:
    st.info(
        "No paper monitor snapshots were found."
    )


# =============================================================================
# RAW DATA SECTION
# =============================================================================

with st.expander("Database Evidence / Raw Tables"):

    st.subheader("paper_sessions")

    st.dataframe(
        sessions_df,
        width="stretch",
        hide_index=True,
    )

    st.subheader("paper_trades")

    st.dataframe(
        trades_df,
        width="stretch",
        hide_index=True,
    )

    st.subheader("paper_risk_events")

    st.dataframe(
        risk_df,
        width="stretch",
        hide_index=True,
    )


# =============================================================================
# FOOTER
# =============================================================================

st.divider()

st.caption(
    "V7 Dashboard — read-only analysis. "
    "No broker connection, order placement, or live-trading authorization."
)