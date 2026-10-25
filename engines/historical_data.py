import pandas as pd


REQUIRED_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
]


class HistoricalDataError(Exception):
    """Raised when historical market data is invalid."""
    pass


class HistoricalDataLoader:
    def __init__(self, minimum_rows=100):
        self.minimum_rows = int(minimum_rows)

    def load_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError as exc:
            raise HistoricalDataError(
                f"CSV file not found: {file_path}"
            ) from exc
        except Exception as exc:
            raise HistoricalDataError(
                f"Could not read CSV file: {exc}"
            ) from exc

        return self.prepare(df)

    def normalize_columns(self, df):
        result = df.copy()

        rename_map = {}

        for column in result.columns:
            cleaned = (
                str(column)
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )
            rename_map[column] = cleaned

        result = result.rename(columns=rename_map)

        aliases = {
            "date": "timestamp",
            "datetime": "timestamp",
            "time": "timestamp",
            "date_time": "timestamp",
            "open_price": "open",
            "high_price": "high",
            "low_price": "low",
            "close_price": "close",
        }

        result = result.rename(columns=aliases)

        return result

    def validate(self, df):
        if df is None:
            raise HistoricalDataError(
                "No historical data was supplied."
            )

        if df.empty:
            raise HistoricalDataError(
                "Historical data is empty."
            )

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing:
            raise HistoricalDataError(
                "Missing required columns: "
                + ", ".join(missing)
            )

        if len(df) < self.minimum_rows:
            raise HistoricalDataError(
                f"Only {len(df)} rows were supplied. "
                f"At least {self.minimum_rows} rows are required."
            )

        if df["timestamp"].isna().any():
            raise HistoricalDataError(
                "Historical data contains invalid timestamps."
            )

        price_columns = [
            "open",
            "high",
            "low",
            "close",
        ]

        for column in price_columns:
            if df[column].isna().any():
                raise HistoricalDataError(
                    f"Column '{column}' contains missing prices."
                )

            if not pd.api.types.is_numeric_dtype(
                df[column]
            ):
                raise HistoricalDataError(
                    f"Column '{column}' is not numeric."
                )

        if (df[price_columns] <= 0).any().any():
            raise HistoricalDataError(
                "Historical data contains zero or negative prices."
            )

        if (df["high"] < df["low"]).any():
            raise HistoricalDataError(
                "Historical data contains candles where "
                "high is below low."
            )

        if (df["high"] < df["open"]).any():
            raise HistoricalDataError(
                "Historical data contains candles where "
                "high is below open."
            )

        if (df["high"] < df["close"]).any():
            raise HistoricalDataError(
                "Historical data contains candles where "
                "high is below close."
            )

        if (df["low"] > df["open"]).any():
            raise HistoricalDataError(
                "Historical data contains candles where "
                "low is above open."
            )

        if (df["low"] > df["close"]).any():
            raise HistoricalDataError(
                "Historical data contains candles where "
                "low is above close."
            )

        if df["timestamp"].duplicated().any():
            raise HistoricalDataError(
                "Historical data contains duplicate timestamps."
            )

        if not df["timestamp"].is_monotonic_increasing:
            raise HistoricalDataError(
                "Historical timestamps are not in ascending order."
            )

        return True

    def prepare(self, df):
        result = self.normalize_columns(df)

        result["timestamp"] = pd.to_datetime(
            result["timestamp"],
            errors="coerce",
        )

        for column in [
            "open",
            "high",
            "low",
            "close",
        ]:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

        result = result.dropna(
            subset=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
            ]
        )

        result = (
            result
            .sort_values("timestamp")
            .drop_duplicates(
                subset=["timestamp"],
                keep="last",
            )
            .reset_index(drop=True)
        )

        self.validate(result)

        return result

    def summary(self, df):
        if df is None or df.empty:
            return {
                "rows": 0,
                "start": None,
                "end": None,
                "days": 0,
            }

        start = df["timestamp"].min()
        end = df["timestamp"].max()

        days = (
            end - start
        ).total_seconds() / 86400.0

        return {
            "rows": len(df),
            "start": start,
            "end": end,
            "days": round(days, 2),
        }


def load_historical_csv(
    file_path,
    minimum_rows=100,
):
    loader = HistoricalDataLoader(
        minimum_rows=minimum_rows
    )

    return loader.load_csv(file_path)


if __name__ == "__main__":
    print("Historical data loader module is working.")