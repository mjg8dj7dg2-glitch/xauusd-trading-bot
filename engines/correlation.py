import pandas as pd


def calculate_returns(df):
    """Calculate percentage returns for a price series."""

    return df["close"].pct_change()


def calculate_correlation(
    primary_df,
    comparison_df,
    window=20,
):
    """
    Calculate rolling correlation between two instruments.

    Both dataframes must contain:
        timestamp
        close
    """

    primary = primary_df[
        ["timestamp", "close"]
    ].copy()

    comparison = comparison_df[
        ["timestamp", "close"]
    ].copy()

    primary["timestamp"] = pd.to_datetime(
        primary["timestamp"]
    )

    comparison["timestamp"] = pd.to_datetime(
        comparison["timestamp"]
    )

    primary["primary_return"] = (
        primary["close"].pct_change()
    )

    comparison["comparison_return"] = (
        comparison["close"].pct_change()
    )

    merged = pd.merge(
        primary[
            ["timestamp", "primary_return"]
        ],
        comparison[
            ["timestamp", "comparison_return"]
        ],
        on="timestamp",
        how="inner",
    )

    merged["correlation"] = (
        merged["primary_return"]
        .rolling(
            window=window,
            min_periods=window,
        )
        .corr(
            merged["comparison_return"]
        )
    )

    return merged


def classify_correlation(
    correlation,
    strong_threshold=0.70,
):
    """Classify the strength and direction of correlation."""

    if pd.isna(correlation):
        return "UNKNOWN"

    if correlation >= strong_threshold:
        return "STRONG_POSITIVE"

    if correlation <= -strong_threshold:
        return "STRONG_NEGATIVE"

    return "WEAK_OR_MODERATE"


def check_correlation_risk(
    correlation,
    maximum_absolute_correlation=0.80,
):
    """
    Determine whether correlation creates a potential
    concentration-risk condition.
    """

    if pd.isna(correlation):
        return False, "Correlation is unknown"

    if (
        abs(correlation)
        >= maximum_absolute_correlation
    ):
        return False, (
            "High correlation exposure detected"
        )

    return True, "Correlation risk check passed"