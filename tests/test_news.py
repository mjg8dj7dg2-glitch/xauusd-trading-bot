from engines.news import (
    create_news_event,
    check_news_risk,
    events_to_dataframe,
)


def main():

    events = [
        create_news_event(
            event_time="2026-01-05 14:30",
            event_name="CPI",
            currency="USD",
            previous=2.7,
            forecast=2.8,
            impact="HIGH",
        ),
        create_news_event(
            event_time="2026-01-05 18:00",
            event_name="GDP",
            currency="USD",
            previous=3.0,
            forecast=3.1,
            impact="HIGH",
        ),
    ]

    current_time = "2026-01-05 14:10"

    allowed, message, event = check_news_risk(
        current_time=current_time,
        events=events,
        before_minutes=30,
        after_minutes=15,
    )

    print("News engine test successful!")
    print()

    print(f"Current time: {current_time}")
    print(f"Trading allowed: {allowed}")
    print(f"Message: {message}")
    print()

    if event:
        print(
            f"Relevant event: "
            f"{event['event_name']}"
        )

        print(
            f"Forecast: "
            f"{event['forecast']}"
        )

        print(
            f"Surprise: "
            f"{event['surprise']}"
        )

    print()
    print("News-event table:")

    print(
        events_to_dataframe(events)
    )


if __name__ == "__main__":
    main()