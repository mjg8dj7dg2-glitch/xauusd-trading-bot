from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    """Standard interface for all market-data sources."""

    @abstractmethod
    def get_data(self, instrument, timeframe):
        """Return market data as a pandas DataFrame."""
        pass


class CSVDataSource(DataSource):
    """Market-data source using a CSV file."""

    def __init__(self, file_path):
        self.file_path = file_path

    def get_data(self, instrument, timeframe):
        df = pd.read_csv(self.file_path)

        df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df


class TestDataSource(DataSource):
    """Small built-in dataset for testing the system."""

    def get_data(self, instrument, timeframe):

        data = {
            "timestamp": pd.date_range(
                start="2026-01-05 09:00",
                periods=10,
                freq="h"
            ),
            "open": [
                2650, 2653, 2658, 2662, 2665,
                2668, 2671, 2674, 2672, 2669
            ],
            "high": [
                2655, 2660, 2664, 2668, 2670,
                2673, 2676, 2678, 2675, 2672
            ],
            "low": [
                2648, 2651, 2655, 2659, 2661,
                2664, 2667, 2670, 2666, 2663
            ],
            "close": [
                2653, 2658, 2662, 2665, 2668,
                2671, 2674, 2672, 2669, 2667
            ],
            "volume": [
                1200, 1350, 1400, 1500, 1600,
                1550, 1700, 1650, 1500, 1450
            ]
        }

        return pd.DataFrame(data)


def get_data_source(source_type, file_path=None):

    if source_type == "csv":
        if not file_path:
            raise ValueError(
                "CSV source requires a file path."
            )

        return CSVDataSource(file_path)

    if source_type == "test":
        return TestDataSource()

    raise ValueError(
        f"Unknown data source: {source_type}"
    )