"""Migration: add job_id column to cards table.

Run with:
    uv run python scripts/migrate_add_job_id.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate() -> None:
    db_path = settings.DATABASE_URL.removeprefix("sqlite+aiosqlite:///")
    logger.info("Connecting to %s", db_path)

    async with aiosqlite.connect(db_path) as conn:
        # Check whether column already exists
        async with conn.execute("PRAGMA table_info(cards)") as cursor:
            columns = {row[1] async for row in cursor}

        if "job_id" in columns:
            logger.info("Column 'job_id' already exists — skipping migration.")
            return

        await conn.execute("ALTER TABLE cards ADD COLUMN job_id TEXT")
        await conn.commit()
        logger.info("Migration complete: added 'job_id' column to cards table.")


if __name__ == "__main__":
    asyncio.run(migrate())
