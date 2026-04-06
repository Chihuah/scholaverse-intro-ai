"""Migration: add history_visible column to cards table.

Run with:
    uv run python scripts/migrate_add_history_visible.py
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

        if "history_visible" in columns:
            logger.info("Column 'history_visible' already exists — skipping.")
            return

        await conn.execute(
            "ALTER TABLE cards ADD COLUMN history_visible BOOLEAN NOT NULL DEFAULT 1"
        )
        await conn.execute("UPDATE cards SET history_visible = 1")
        await conn.commit()
        logger.info("Migration complete: added 'history_visible' to cards table.")


if __name__ == "__main__":
    asyncio.run(migrate())
