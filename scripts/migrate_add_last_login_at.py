"""Migration: add last_login_at column to students table."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scholaverse.db"


def run() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(students)")
    columns = {row[1] for row in cursor.fetchall()}

    if "last_login_at" in columns:
        print("Column 'last_login_at' already exists — skipping.")
    else:
        cursor.execute("ALTER TABLE students ADD COLUMN last_login_at DATETIME")
        conn.commit()
        print("Added column 'last_login_at' to students table.")

    conn.close()


if __name__ == "__main__":
    run()
