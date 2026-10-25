from datetime import datetime, timedelta

import pandas as pd


HIGH_IMPACT_EVENTS = {
    "CPI",
    "FOMC",
    "NFP",
    "PPI",
    "GDP",
    "INTEREST_RATE_DECISION",
}


def create_news_event(
    event_time,
    event_name,
    currency=None,
    previous=None,
    forecast=None,
    actual=None,
    impact="MEDIUM",
):
    """
    Create a standardized economic-news event.
    """

    event = {
        "event_time": pd.to_datetime(event_time),
        "event_name": event_name.upper(),
        "currency": currency,
        "previous": previous,
        "forecast": forecast,
        "actual": actual,
        "impact": impact.upper(),
    }

    if forecast is not None and actual is not None:
        event["surprise"] = actual - forecast
    else:
        event["surprise"] = None

    return event


def is_high_impact_event(event):
    """Determine whether an event should receive high-impact treatment."""

    if event is None:
        return False

    event_name = str(
        event.get("event_name", "")
    ).upper()

    impact = str(
        event.get("impact", "")
    ).upper()

    return (
        event_name in HIGH_IMPACT_EVENTS
        or impact == "HIGH"
    )


def minutes_until_event(
    current_time,
    event_time,
):
    """Calculate minutes until an economic event."""

    current = pd.to_datetime(current_time)
    event = pd.to_datetime(event_time)

    difference = event - current

    return difference.total_seconds() / 60


def check_news_risk(
    current_time,
    events,
    before_minutes=30,
    after_minutes=15,
):
    """
    Check whether a high-impact news event is close enough
    to create a potential trading-risk condition.

    Returns:
        allowed: True/False
        message: explanation
        event: relevant event or None
    """

    current_time = pd.to_datetime(current_time)

    if not events:
        return True, "No scheduled news events", None

    for event in events:

        if not is_high_impact_event(event):
            continue

        event_time = pd.to_datetime(
            event["event_time"]
        )

        minutes = minutes_until_event(
            current_time,
            event_time,
        )

        if (
            -after_minutes
            <= minutes
            <= before_minutes
        ):
            return (
                False,
                (
                    "High-impact news risk: "
                    f"{event['event_name']} "
                    f"is {minutes:.1f} minutes from "
                    "the current time"
                ),
                event,
            )

    return (
        True,
        "No high-impact news risk detected",
        None,
    )


def events_to_dataframe(events):
    """Convert standardized events into a DataFrame."""

    if not events:
        return pd.DataFrame(
            columns=[
                "event_time",
                "event_name",
                "currency",
                "previous",
                "forecast",
                "actual",
                "surprise",
                "impact",
            ]
        )

    return pd.DataFrame(events)