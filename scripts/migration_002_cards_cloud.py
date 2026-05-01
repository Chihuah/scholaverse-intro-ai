"""Migration 002 (web-server): add cloud-generation columns to cards.

Idempotent. Run on vm-web-server:
    /var/www/app.scholaverse.cc/intro-ai/.venv/bin/python _migration_002_cards_cloud.py
"""

import sqlite3
import sys

DB_PATH = "/var/www/app.scholaverse.cc/intro-ai/data/scholaverse.db"

MIGRATIONS = [
    "ALTER TABLE cards ADD COLUMN backend_used TEXT NOT NULL DEFAULT 'local'",
    "ALTER TABLE cards ADD COLUMN cloud_model TEXT",
    "ALTER TABLE cards ADD COLUMN cloud_mode TEXT",
    "ALTER TABLE cards ADD COLUMN fallback_from_cloud BOOLEAN NOT NULL DEFAULT 0",
    "ALTER TABLE cards ADD COLUMN cloud_error TEXT",
    "ALTER TABLE cards ADD COLUMN reference_card_id INTEGER",
]


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        print(f"Pre-migration cards rows: {rows}")

        for sql in MIGRATIONS:
            try:
                conn.execute(sql)
                print(f"OK: {sql}")
            except sqlite3.OperationalError as exc:
                print(f"SKIP: {sql} -> {exc}")

        conn.commit()

        print("\n--- new schema ---")
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='cards'"
        ).fetchone()
        if row:
            print(row[0])
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
