import os
import sqlite3
import pandas as pd


REQUIRED_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
]

OPTIONAL_COLUMNS = [
    "volume",
]


def _normalize_column_name(column):
    """
    Convert a CSV column name into a consistent format.
    """
    column = str(column).strip()
    column = column.replace("\ufeff", "")
    column = column.lower()
    column = column.replace(" ", "_")
    column = column.replace("-", "_")

    return column


def _normalize_columns(df):
    """
    Normalize column names and identify common timestamp aliases.
    """
    result = df.copy()

    result.columns = [
        _normalize_column_name(column)
        for column in result.columns
    ]

    # Common timestamp column aliases.
    timestamp_aliases = [
        "timestamp",
        "datetime",
        "datetime_utc",
        "date_time",
        "time",
        "date",
        "datetimestamp",
        "unix_timestamp",
        "unix_time",
    ]

    # If timestamp already exists, nothing else is needed.
    if "timestamp" not in result.columns:

        for alias in timestamp_aliases:
            if alias in result.columns:
                result = result.rename(
                    columns={
                        alias: "timestamp"
                    }
                )
                break

    # Some datasets have separate date and time columns.
    if (
        "timestamp" not in result.columns
        and "date" in result.columns
        and "time" in result.columns
    ):
        result["timestamp"] = (
            result["date"].astype(str)
            + " "
            + result["time"].astype(str)
        )

    return result


def _convert_unix_timestamp(series):
    """
    Convert a numeric Unix timestamp into datetime.

    Automatically determines whether the values are:
    seconds, milliseconds, microseconds, or nanoseconds.
    """
    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid = numeric.dropna()

    if valid.empty:
        return pd.to_datetime(
            series,
            errors="coerce",
            utc=True,
        )

    median_value = abs(float(valid.median()))

    if median_value >= 1e18:
        unit = "ns"
    elif median_value >= 1e15:
        unit = "us"
    elif median_value >= 1e12:
        unit = "ms"
    else:
        unit = "s"

    return pd.to_datetime(
        numeric,
        unit=unit,
        errors="coerce",
        utc=True,
    )


def _convert_timestamp(series):
    """
    Convert a timestamp column into pandas datetime.
    """
    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    numeric_ratio = numeric.notna().mean()

    # If almost all values are numeric, treat them as Unix timestamps.
    if numeric_ratio >= 0.95:
        return _convert_unix_timestamp(series)

    return pd.to_datetime(
        series,
        errors="coerce",
        utc=True,
    )


def _validate_required_columns(df):
    """
    Check that all required market-data columns exist.
    """
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )


def _validate_ohlc(df):
    """
    Validate OHLC market data.
    """
    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in price_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[price_columns].isnull().any().any():
        raise ValueError(
            "Market data contains missing or invalid OHLC values."
        )

    invalid_high_low = (
        df["high"] < df["low"]
    )

    invalid_high_open = (
        df["high"] < df["open"]
    )

    invalid_high_close = (
        df["high"] < df["close"]
    )

    invalid_low_open = (
        df["low"] > df["open"]
    )

    invalid_low_close = (
        df["low"] > df["close"]
    )

    if invalid_high_low.any():
        raise ValueError(
            "Invalid candle detected: high is below low."
        )

    if invalid_high_open.any():
        raise ValueError(
            "Invalid candle detected: high is below open."
        )

    if invalid_high_close.any():
        raise ValueError(
            "Invalid candle detected: high is below close."
        )

    if invalid_low_open.any():
        raise ValueError(
            "Invalid candle detected: low is above open."
        )

    if invalid_low_close.any():
        raise ValueError(
            "Invalid candle detected: low is above close."
        )


def load_csv(file_path):
    """
    Load historical OHLCV data from a CSV file.

    The loader accepts common timestamp column names and
    normalizes them to:

        timestamp
        open
        high
        low
        close
        volume
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Market-data file was not found: {file_path}"
        )

    try:
        df = pd.read_csv(
            file_path,
            sep=None,
            engine="python",
        )
    except Exception as exc:
        raise ValueError(
            f"Could not read CSV file: {exc}"
        ) from exc

    if df.empty:
        raise ValueError(
            "Market-data CSV file is empty."
        )

    df = _normalize_columns(df)

    _validate_required_columns(df)

    df["timestamp"] = _convert_timestamp(
        df["timestamp"]
    )

    if df["timestamp"].isnull().any():
        invalid_count = int(
            df["timestamp"].isnull().sum()
        )

        raise ValueError(
            "Could not parse "
            f"{invalid_count} timestamp values."
        )

    # Normalize OHLC columns.
    _validate_ohlc(df)

    # Normalize volume when present.
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(
            df["volume"],
            errors="coerce",
        )

    # Sort chronologically.
    df = df.sort_values(
        "timestamp"
    ).reset_index(
        drop=True
    )

    # Remove duplicate timestamps.
    df = df.drop_duplicates(
        subset=["timestamp"],
        keep="first",
    ).reset_index(
        drop=True
    )

    # Make sure timestamp is the first column.
    preferred_columns = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    existing_preferred = [
        column
        for column in preferred_columns
        if column in df.columns
    ]

    remaining_columns = [
        column
        for column in df.columns
        if column not in existing_preferred
    ]

    df = df[
        existing_preferred
        + remaining_columns
    ]

    return df


def validate_market_data(df):
    """
    Validate an already-loaded market-data DataFrame.

    Returns:
        (True, message)
    or:
        (False, message)
    """

    if df is None:
        return False, "Market data is None."

    if df.empty:
        return False, "Market data is empty."

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        return (
            False,
            f"Missing required columns: {missing_columns}",
        )

    if df["timestamp"].isnull().any():
        return False, "Timestamp contains invalid values."

    price_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    if df[price_columns].isnull().any().any():
        return False, "OHLC data contains missing values."

    if (df["high"] < df["low"]).any():
        return False, "Invalid candle: high below low."

    if (df["high"] < df["open"]).any():
        return False, "Invalid candle: high below open."

    if (df["high"] < df["close"]).any():
        return False, "Invalid candle: high below close."

    if (df["low"] > df["open"]).any():
        return False, "Invalid candle: low above open."

    if (df["low"] > df["close"]).any():
        return False, "Invalid candle: low above close."

    if not df["timestamp"].is_monotonic_increasing:
        return False, "Timestamps are not chronological."

    return True, "Market data validation passed."


def save_market_data_to_database(
    df,
    database_path="trading_bot.db",
    table_name="market_data",
):
    """
    Save market data into SQLite.
    """

    if df is None or df.empty:
        raise ValueError(
            "Cannot save empty market data."
        )

    valid, message = validate_market_data(df)

    if not valid:
        raise ValueError(message)

    connection = sqlite3.connect(
        database_path
    )

    try:
        df.to_sql(
            table_name,
            connection,
            if_exists="append",
            index=False,
        )
    finally:
        connection.close()


def load_market_data_from_database(
    database_path="trading_bot.db",
    table_name="market_data",
):
    """
    Load market data from SQLite.
    """

    if not os.path.exists(database_path):
        raise FileNotFoundError(
            f"Database was not found: {database_path}"
        )

    connection = sqlite3.connect(
        database_path
    )

    try:
        query = f"""
        SELECT *
        FROM {table_name}
        ORDER BY timestamp
        """

        df = pd.read_sql_query(
            query,
            connection,
        )
    finally:
        connection.close()

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
            utc=True,
        )

    return df


def get_market_data_summary(df):
    """
    Return a simple summary of a market-data DataFrame.
    """

    if df is None or df.empty:
        return {
            "rows": 0,
            "start": None,
            "end": None,
            "columns": [],
        }

    return {
        "rows": len(df),
        "start": df["timestamp"].iloc[0],
        "end": df["timestamp"].iloc[-1],
        "columns": list(df.columns),
    }


if __name__ == "__main__":
    print(
        "Market-data module loaded successfully."
    )