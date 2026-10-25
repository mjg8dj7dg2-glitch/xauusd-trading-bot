
import sqlite3
import json
from pathlib import Path

db_path = Path("trading_bot.db")
conn = sqlite3.connect(
    f"file:{db_path.resolve().as_posix()}?mode=ro",
    uri=True,
)

try:
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            timestamp,
            event_type,
            severity,
            message,
            blocked,
            allowed,
            reason,
            metadata,
            metadata_json,
            event_json,
            risk_json
        FROM paper_risk_events
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if row is None:
        print("No risk-event rows found.")
    else:
        names = [item[0] for item in cur.description]

        for name, value in zip(names, row):
            print(f"\n--- {name} ---")

            if name in ("metadata", "metadata_json", "event_json", "risk_json"):
                try:
                    value = json.dumps(
                        json.loads(value),
                        indent=2,
                    ) if value else value
                except (json.JSONDecodeError, TypeError):
                    pass

            print(value)

    print("\nRead-only inspection complete.")

finally:
    conn.close()
