from pathlib import Path

import pytest

from engines.market_data import load_csv, validate_market_data


FILE_PATH = Path("data/test_gold.csv")


def test_load_csv_returns_expected_candles():
    df = load_csv(str(FILE_PATH))

    assert len(df) == 10
    assert {"timestamp", "open", "high", "low", "close"}.issubset(df.columns)


def test_timestamps_are_valid_and_chronological():
    df = load_csv(str(FILE_PATH))

    assert df["timestamp"].notna().all()
    assert df["timestamp"].is_monotonic_increasing


def test_market_data_validation_passes():
    df = load_csv(str(FILE_PATH))

    valid, message = validate_market_data(df)

    assert valid, message


def test_missing_file_raises_error():
    with pytest.raises(FileNotFoundError):
        load_csv(str(FILE_PATH.parent / "missing_test_file.csv"))
