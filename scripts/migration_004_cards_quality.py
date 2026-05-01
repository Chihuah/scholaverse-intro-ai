"""Migration 004 (web-server): add cloud_quality column to cards.

Idempotent. Run on vm-web-server:
    /var/www/app.scholaverse.cc/intro-ai/.venv/bin/python _migration_004_cards_quality.py
"""

import sqlite3
import sys

DB_PATH = "/var/www/app.scholaverse.cc/intro-ai/data/scholaverse.db"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        try:
            conn.execute("ALTER TABLE cards ADD COLUMN cloud_quality TEXT")
            print("OK: ADD COLUMN cloud_quality TEXT")
        except sqlite3.OperationalError as exc:
            print(f"SKIP: {exc}")
        conn.commit()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
