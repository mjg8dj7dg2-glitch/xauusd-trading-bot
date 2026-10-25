import sqlite3
import tempfile
from pathlib import Path


def test_database():
    with tempfile.TemporaryDirectory(prefix="strategy_db_test_") as temp_dir:
        database_path = Path(temp_dir) / "test.db"
        connection = sqlite3.connect(database_path)

        try:
            connection.execute("""
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    instrument TEXT,
                    timeframe TEXT,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            connection.execute("""
                INSERT INTO strategies
                    (name, description, instrument, timeframe, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "Test Strategy",
                "Database test strategy",
                "XAUUSD",
                "1H",
                "TEST",
            ))

            result = connection.execute("""
                SELECT name, instrument, timeframe, status
                FROM strategies
                WHERE name = ?
            """, ("Test Strategy",)).fetchone()

            assert result == (
                "Test Strategy",
                "XAUUSD",
                "1H",
                "TEST",
            )
        finally:
            connection.close()


if __name__ == "__main__":
    test_database()
