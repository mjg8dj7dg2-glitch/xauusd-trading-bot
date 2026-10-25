import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from engines.market_data import validate_market_data

API_URL = "https://api.twelvedata.com/time_series"
SYMBOL = "XAU/USD"
INTERVAL = "1h"
OUTPUT_SIZE = 200


def fetch_closed_candles():
    api_key = os.environ.get("TWELVE_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("TWELVE_DATA_API_KEY environment variable is missing.")

    response = requests.get(
        API_URL,
        params={
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "outputsize": OUTPUT_SIZE,
            "timezone": "UTC",
            "apikey": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") == "error" or "values" not in payload:
        raise RuntimeError(
            "Market data API error: " + str(payload.get("message", payload))
        )

    df = pd.DataFrame(payload["values"])
    required = ["datetime", "open", "high", "low", "close"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"API response is missing columns: {missing}")

    df = df.rename(columns={"datetime": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")

    now = datetime.now(timezone.utc)
    candle_duration = timedelta(hours=1)
    df = df[df["timestamp"] + candle_duration <= pd.Timestamp(now)]
    df = df.reset_index(drop=True)

    if df.empty:
        raise RuntimeError("No fully closed hourly candles were returned.")

    valid, message = validate_market_data(df)
    if not valid:
        raise ValueError(f"Market data validation failed: {message}")

    return df


if __name__ == "__main__":
    candles = fetch_closed_candles()
    print("Mode: DATA CHECK ONLY — NO TRADES")
    print(f"Symbol: {SYMBOL}")
    print(f"Closed candles: {len(candles)}")
    print(f"Oldest UTC candle: {candles['timestamp'].iloc[0]}")
    print(f"Latest closed UTC candle: {candles['timestamp'].iloc[-1]}")
    print(f"Current UTC time: {datetime.now(timezone.utc).isoformat()}")
