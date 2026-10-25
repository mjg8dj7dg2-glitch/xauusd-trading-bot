
"""Isolated XAU/USD multi-timeframe runner.
Signal generation only: no orders and no database writes.
"""

import json
import sqlite3
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from engines.market_data import validate_market_data
from engines.technical import add_technical_features
from engines.regime import add_market_regime
from engines.strategy import generate_signals


BASE_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = (BASE_DIR / "paper_trading_test.db").resolve()
PRODUCTION_DB_PATH = (BASE_DIR / "trading_bot.db").resolve()

SESSION_ID = "XAU_TEST_20261013T005206_fb65691d"
EXPECTED_STRATEGY = "XAUUSD_HOURLY_PAPER_TEST"
API_URL = "https://api.twelvedata.com/time_series"

TIMEFRAMES = {
    "1h": pd.Timedelta(hours=1),
    "30min": pd.Timedelta(minutes=30),
    "15min": pd.Timedelta(minutes=15),
}



def validate_configuration():
    if TEST_DB_PATH == PRODUCTION_DB_PATH:
        raise RuntimeError("Safety stop: database paths match.")

    if TEST_DB_PATH.name != "paper_trading_test.db":
        raise RuntimeError("Safety stop: unexpected database filename.")

    if not TEST_DB_PATH.is_file():
        raise RuntimeError("Safety stop: test database does not exist.")

    if not os.environ.get("TWELVE_DATA_API_KEY"):
        raise RuntimeError("Safety stop: TWELVE_DATA_API_KEY is missing.")

    # Open the existing test database in SQLite read-only mode.
    database_uri = TEST_DB_PATH.as_uri() + "?mode=ro"

    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT session_id, strategy_name, status, metadata_json
            FROM paper_sessions
            WHERE session_id = ?
            """,
            (SESSION_ID,),
        ).fetchone()

    if row is None:
        raise RuntimeError("Safety stop: expected test session not found.")

    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Safety stop: session metadata is invalid JSON."
        ) from exc

    session = dict(row)
    session["metadata"] = metadata

    if session.get("strategy_name") != EXPECTED_STRATEGY:
        raise RuntimeError("Safety stop: strategy mismatch.")

    if session.get("status") != "RUNNING":
        raise RuntimeError("Safety stop: test session is not RUNNING.")

    if (
        metadata.get("symbol") != "XAU/USD"
        or metadata.get("interval") != "1h"
        or metadata.get("live_trading") is not False
        or metadata.get("orders_enabled") is not False
    ):
        raise RuntimeError("Safety stop: paper-only settings mismatch.")

    return session



def fetch_closed_candles(interval, duration):
    params = urllib.parse.urlencode({
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": 200,
        "timezone": "UTC",
        "apikey": os.environ["TWELVE_DATA_API_KEY"],
    })

    request = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "XAUUSD-Paper-Signal-Check/1.0"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") == "error" or "values" not in payload:
        message = str(payload.get("message", "Unexpected API response"))
        raise RuntimeError(
            f"Twelve Data request failed for {interval}: {message[:250]}"
        )

    df = pd.DataFrame(payload["values"])
    required = ["datetime", "open", "high", "low", "close"]

    if any(column not in df.columns for column in required):
        raise RuntimeError(
            f"Safety stop: {interval} response has missing columns."
        )

    df["datetime"] = pd.to_datetime(
        df["datetime"], utc=True, errors="raise"
    )

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="raise")

    if df.empty or df[required].isna().any().any():
        raise RuntimeError(
            f"Safety stop: {interval} data is empty or incomplete."
        )

    if df["datetime"].duplicated().any():
        raise RuntimeError(
            f"Safety stop: duplicate {interval} candle timestamps."
        )

    if not (
        (df["high"] >= df[["open", "close", "low"]].max(axis=1)).all()
        and (df["low"] <= df[["open", "close", "high"]].min(axis=1)).all()
    ):
        raise RuntimeError(
            f"Safety stop: invalid {interval} OHLC relationships."
        )

    now = pd.Timestamp(datetime.now(timezone.utc))

    # Candle timestamps are opening times; exclude candles not fully closed.
    closed = df.loc[df["datetime"] + duration <= now].copy()
    closed = closed.sort_values("datetime").reset_index(drop=True)
    closed = closed.rename(columns={"datetime": "timestamp"})

    if closed.empty:
        raise RuntimeError(
            f"Safety stop: no fully closed {interval} candles."
        )

    is_valid, message = validate_market_data(closed)
    if not is_valid:
        raise RuntimeError(f"Safety stop for {interval}: {message}")

    print(f"{interval} market-data validation: {message}")
    return closed


def analyse_timeframe(interval, duration):
    candles = fetch_closed_candles(interval, duration)

    featured = add_technical_features(candles)
    featured = add_market_regime(featured)
    latest = featured.iloc[-1]

    indicators = ["sma", "ema", "rsi", "atr"]
    if latest[indicators].isna().any():
        raise RuntimeError(
            f"Safety stop: incomplete {interval} indicators."
        )

    if (
        latest["trend_regime"] == "UNKNOWN"
        or latest["volatility_regime"] == "UNKNOWN"
    ):
        signal = "NO_SIGNAL"
        reason = "Regime classification unknown; signal suppressed."
    else:
        signalled = generate_signals(featured)
        latest_signal = signalled.iloc[-1]
        signal = str(latest_signal["signal"])
        reason = str(latest_signal["signal_reason"])

    return {
        "interval": interval,
        "candle_count": len(featured),
        "timestamp": latest["timestamp"].isoformat(),
        "close": float(latest["close"]),
        "sma": float(latest["sma"]),
        "ema": float(latest["ema"]),
        "rsi": float(latest["rsi"]),
        "atr": float(latest["atr"]),
        "trend": str(latest["trend_regime"]),
        "volatility": str(latest["volatility_regime"]),
        "signal": signal,
        "reason": reason or "No strategy conditions met.",
    }


if __name__ == "__main__":
    session = validate_configuration()

    print("Configuration check passed.")
    print("Mode: PAPER ONLY — SIGNAL GENERATION ONLY")
    print("Production database selected: False")
    print("Session:", session["session_id"])
    print("")

    results = []

    # Each timeframe is fetched and analysed independently.
    for interval, duration in TIMEFRAMES.items():
        try:
            result = analyse_timeframe(interval, duration)
            results.append(result)

            print(f"--- {interval} ---")
            print("Closed candles:", result["candle_count"])
            print("Latest closed candle UTC:", result["timestamp"])
            print("Latest close:", round(result["close"], 4))
            print("SMA:", round(result["sma"], 4))
            print("EMA:", round(result["ema"], 4))
            print("RSI:", round(result["rsi"], 4))
            print("ATR:", round(result["atr"], 4))
            print("Trend regime:", result["trend"])
            print("Volatility regime:", result["volatility"])
            print("Strategy signal:", result["signal"])
            print("Signal reason:", result["reason"])
            print("")

        except Exception as exc:
            # Report a timeframe failure without hiding it or inventing a signal.
            print(f"--- {interval} ---")
            print("ANALYSIS FAILED:", str(exc))
            print("No signal reported for this timeframe.")
            print("")

    print("--- Safety summary ---")
    print("Timeframes successfully analysed:", len(results), "of", len(TIMEFRAMES))
    print("Orders enabled: False")
    print("Database writes: NONE")
    print("Trades created: NONE")
