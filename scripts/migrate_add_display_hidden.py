"""Migration: add is_display and is_hidden columns to cards table.

Run with:
    uv run python scripts/migrate_add_display_hidden.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate() -> None:
    db_path = settings.DATABASE_URL.removeprefix("sqlite+aiosqlite:///")
    logger.info("Connecting to %s", db_path)

    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("PRAGMA table_info(cards)") as cursor:
            columns = {row[1] async for row in cursor}

        added = []

        if "is_display" not in columns:
            await conn.execute(
                "ALTER TABLE cards ADD COLUMN is_display BOOLEAN NOT NULL DEFAULT 0"
            )
            added.append("is_display")
        else:
            logger.info("Column 'is_display' already exists — skipping.")

        if "is_hidden" not in columns:
            await conn.execute(
                "ALTER TABLE cards ADD COLUMN is_hidden BOOLEAN NOT NULL DEFAULT 0"
            )
            added.append("is_hidden")
        else:
            logger.info("Column 'is_hidden' already exists — skipping.")

        if "is_display" in added:
            # Backfill: mirror is_latest -> is_display for existing cards
            await conn.execute("UPDATE cards SET is_display = is_latest")
            logger.info("Backfilled is_display = is_latest for existing cards.")

        await conn.commit()

        if added:
            logger.info("Migration complete: added columns %s to cards table.", added)
        else:
            logger.info("Nothing to migrate.")


if __name__ == "__main__":
    asyncio.run(migrate())
