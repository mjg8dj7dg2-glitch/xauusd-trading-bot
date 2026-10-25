from __future__ import annotations

from math import isfinite

from engines.paper_history import PaperHistoryAnalyzer
from engines.paper_persistence import PaperPersistence
from engines.paper_evaluation import PaperSessionEvaluator


DB_PATH = "trading_bot.db"
V7_STRATEGY = "XAUUSD_V7_PAPER_TEST"


def number(value, default=0.0):
    try:
        value = float(value)
        if isfinite(value):
            return value
    except (TypeError, ValueError):
        pass

    return float(default)


def max_drawdown_from_equity(equity_curve):
    """
    Calculate maximum percentage drawdown from persisted equity.
    """
    peak = None
    maximum_drawdown = 0.0

    for point in equity_curve:
        equity = number(
            point.get("equity")
            if isinstance(point, dict)
            else point,
            default=float("nan"),
        )

        if not isfinite(equity) or equity <= 0:
            continue

        if peak is None or equity > peak:
            peak = equity
            continue

        drawdown = (peak - equity) / peak

        if drawdown > maximum_drawdown:
            maximum_drawdown = drawdown

    return maximum_drawdown


def print_separator(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_history_summary(history):
    aggregate = history.get("aggregate", {})
    quality = history.get("quality", {})
    unique = quality.get("unique_evidence", {})

    print_separator("V7 PAPER OBSERVATION REPORT")

    print(f"Strategy filter: {V7_STRATEGY}")

    print()
    print("STORED HISTORY")
    print("-" * 80)

    print(f"Stored sessions : {aggregate.get('sessions', 0)}")
    print(f"Stored trades   : {aggregate.get('trades', 0)}")
    print(f"Wins            : {aggregate.get('wins', 0)}")
    print(f"Losses          : {aggregate.get('losses', 0)}")
    print(f"P&L             : {number(aggregate.get('pnl')):+,.2f}")
    print(f"Win rate        : {number(aggregate.get('win_rate')):.2%}")
    print(f"Profit factor   : {number(aggregate.get('profit_factor')):.4f}")

    print()
    print("EVIDENCE QUALITY")
    print("-" * 80)

    print(f"Stored runs     : {quality.get('stored_sessions', 0)}")
    print(f"Unique runs     : {quality.get('unique_runs', 0)}")
    print(f"Duplicate runs  : {quality.get('duplicate_runs', 0)}")
    print(f"Empty runs      : {quality.get('empty_runs', 0)}")

    print()
    print("UNIQUE V7 PAPER EVIDENCE")
    print("-" * 80)

    print(f"Unique sessions : {unique.get('sessions', 0)}")
    print(f"Unique trades   : {unique.get('trades', 0)}")
    print(f"Wins            : {unique.get('wins', 0)}")
    print(f"Losses          : {unique.get('losses', 0)}")
    print(f"P&L             : {number(unique.get('pnl')):+,.2f}")
    print(f"Win rate        : {number(unique.get('win_rate')):.2%}")
    print(f"Profit factor   : {number(unique.get('profit_factor')):.4f}")


def evaluate_unique_sessions(history, persistence):
    """
    Evaluate only unique V7 paper sessions.

    PaperHistoryAnalyzer already identifies duplicate fingerprints.
    We use the first occurrence of each fingerprint as the canonical
    evidence run.
    """
    sessions = history.get("sessions", [])

    seen_fingerprints = set()
    unique_sessions = []

    for session in sessions:
        fingerprint = session.get("fingerprint")

        if fingerprint in seen_fingerprints:
            continue

        seen_fingerprints.add(fingerprint)
        unique_sessions.append(session)

    evaluator = PaperSessionEvaluator()

    results = []

    print_separator("UNIQUE SESSION EVALUATIONS")

    for index, session in enumerate(unique_sessions, start=1):
        session_id = session.get("session_id")

        stored_session = persistence.get_session(session_id)

        if stored_session is None:
            print(f"Session {session_id}: NOT FOUND")
            continue

        trades = persistence.get_trades(session_id)
        equity_curve = persistence.get_equity_curve(session_id)
        risk_events = persistence.get_risk_events(session_id)
        monitor_snapshots = persistence.get_monitor_snapshots(session_id)

        max_dd = max_drawdown_from_equity(equity_curve)

        initial_balance = number(
            stored_session.get("initial_balance")
        )

        final_balance = number(
            stored_session.get("final_balance"),
            default=initial_balance,
        )

        report = {
            "strategy_name": stored_session.get(
                "strategy_name",
                V7_STRATEGY,
            ),
            "mode": "PAPER",
            "live_trading": False,
            "account": {
                "initial_balance": initial_balance,
                "final_balance": final_balance,
                "max_drawdown": max_dd,
            },
            "performance": {
                "initial_balance": initial_balance,
                "final_balance": final_balance,
                "pnl": final_balance - initial_balance,
                "max_drawdown": max_dd,
            },
            "trades": trades,
            "equity_curve": equity_curve,
            "risk": {
                "events": len(risk_events),
            },
        }

        evaluation = evaluator.evaluate(report)

        account = evaluation.get("account", {})
        statistics = evaluation.get("trades", {})
        streak = evaluation.get("losing_streak", {})

        print()
        print(f"SESSION {index}")
        print("-" * 80)

        print(f"Session ID       : {session_id}")
        print(
            f"Strategy         : "
            f"{stored_session.get('strategy_name')}"
        )
        print(
            f"Initial balance  : "
            f"{number(account.get('initial_balance')):,.2f}"
        )
        print(
            f"Final balance    : "
            f"{number(account.get('final_balance')):,.2f}"
        )
        print(
            f"P&L              : "
            f"{number(account.get('total_pnl')):+,.2f}"
        )
        print(
            f"Return           : "
            f"{number(account.get('return_pct')):+.2f}%"
        )
        print(
            f"Max drawdown     : "
            f"{number(account.get('max_drawdown')):.2%}"
        )
        print(
            f"Trades           : "
            f"{statistics.get('total_trades', 0)}"
        )
        print(
            f"Wins             : "
            f"{statistics.get('winning_trades', 0)}"
        )
        print(
            f"Losses           : "
            f"{statistics.get('losing_trades', 0)}"
        )
        print(
            f"Win rate         : "
            f"{number(statistics.get('win_rate')):.2%}"
        )
        print(
            f"Profit factor    : "
            f"{number(statistics.get('profit_factor')):.4f}"
        )
        print(
            f"Average trade    : "
            f"{number(statistics.get('average_trade')):+,.2f}"
        )
        print(
            f"Max losing streak: "
            f"{streak.get('maximum', 0)}"
        )
        print(
            f"Equity points    : "
            f"{len(equity_curve)}"
        )
        print(
            f"Risk events      : "
            f"{len(risk_events)}"
        )
        print(
            f"Monitor snapshots: "
            f"{len(monitor_snapshots)}"
        )
        print(
            f"Evaluation       : "
            f"{evaluation.get('status')}"
        )

        reasons = evaluation.get("reasons", [])

        if reasons:
            print()
            print("Evaluation warnings:")
            for reason in reasons:
                print(f"  - {reason}")
        else:
            print()
            print("Evaluation warnings: none")

        # Direction breakdown
        direction = evaluation.get("direction", {})

        if direction:
            print()
            print("Direction performance:")

            for name, stats in direction.items():
                print(
                    f"  {name}: "
                    f"{stats.get('total_trades', 0)} trades | "
                    f"WR={number(stats.get('win_rate')):.2%} | "
                    f"PF={number(stats.get('profit_factor')):.4f} | "
                    f"P&L={number(stats.get('total_pnl')):+,.2f}"
                )

        # Regime breakdown
        regime = evaluation.get("regime", {})

        for regime_type in ("trend", "volatility"):
            groups = regime.get(regime_type, {})

            if not groups:
                continue

            print()
            print(
                f"{regime_type.title()} regime performance:"
            )

            for name, stats in groups.items():
                print(
                    f"  {name}: "
                    f"{stats.get('total_trades', 0)} trades | "
                    f"WR={number(stats.get('win_rate')):.2%} | "
                    f"PF={number(stats.get('profit_factor')):.4f} | "
                    f"P&L={number(stats.get('total_pnl')):+,.2f}"
                )

        results.append(
            {
                "session_id": session_id,
                "evaluation": evaluation,
                "max_drawdown": max_dd,
                "trades": trades,
                "equity_points": len(equity_curve),
                "risk_events": len(risk_events),
                "monitor_snapshots": len(monitor_snapshots),
            }
        )

    return results


def print_observation_decision(history, evaluations):
    quality = history.get("quality", {})
    unique = quality.get("unique_evidence", {})

    unique_sessions = int(unique.get("sessions", 0))
    unique_trades = int(unique.get("trades", 0))

    print_separator("OBSERVATION READINESS")

    if unique_sessions == 0:
        print("Status: NO_V7_OBSERVATION")
        print("No unique V7 paper observation exists.")
        return

    if unique_sessions == 1:
        print("Status: SINGLE_RUN_OBSERVATION")
        print(
            "V7 has one independent paper-observation run."
        )
        print(
            f"Unique evidence: {unique_trades} trades."
        )

        if evaluations:
            evaluation = evaluations[0]["evaluation"]
            print(
                f"Session evaluation: "
                f"{evaluation.get('status')}"
            )

        print()
        print(
            "Decision: continue paper observation."
        )
        print(
            "Do not promote V7 based on one independent paper run."
        )
        return

    print("Status: MULTI_SESSION_OBSERVATION")
    print(
        f"Independent sessions: {unique_sessions}"
    )
    print(
        f"Unique trades: {unique_trades}"
    )

    if len(evaluations) >= 2:
        statuses = [
            item["evaluation"].get("status")
            for item in evaluations
        ]

        print(
            f"Session evaluations: {', '.join(statuses)}"
        )

    print()
    print(
        "Decision: begin cross-session stability review."
    )
    print(
        "This still does not automatically authorize live trading."
    )


def main():
    persistence = PaperPersistence(DB_PATH)
    persistence.ensure_tables()

    analyzer = PaperHistoryAnalyzer(DB_PATH)

    history = analyzer.analyze(
        strategy_name=V7_STRATEGY
    )

    print_history_summary(history)

    evaluations = evaluate_unique_sessions(
        history,
        persistence,
    )

    print_observation_decision(
        history,
        evaluations,
    )

    print_separator("V7 PAPER OBSERVATION CONCLUSION")

    quality = history.get("quality", {})
    unique = quality.get("unique_evidence", {})

    unique_sessions = int(unique.get("sessions", 0))
    unique_trades = int(unique.get("trades", 0))

    if unique_sessions == 1:
        print("ONE UNIQUE PAPER RUN")
        print(
            f"V7 has {unique_trades} unique paper trades."
        )
        print(
            "The duplicate stored run is correctly excluded."
        )
        print(
            "Drawdown is now calculated from the persisted "
            "equity curve."
        )
        print(
            "Continue collecting independent paper sessions."
        )

    elif unique_sessions >= 2:
        print("MULTI-SESSION PAPER OBSERVATION")
        print(
            f"V7 has {unique_sessions} unique sessions "
            f"and {unique_trades} unique trades."
        )
        print(
            "Proceed to cross-session stability analysis."
        )

    else:
        print("NO UNIQUE V7 PAPER EVIDENCE")

    print()
    print(
        "Robustness sessions are intentionally excluded because "
        "their strategy names are different."
    )
    print(
        "This report is analysis-only and performs no live trading."
    )


if __name__ == "__main__":
    main()