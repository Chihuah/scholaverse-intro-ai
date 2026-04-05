"""Migration: add prompt debug fields to cards table.

Run with:
    uv run python scripts/migrate_add_prompt_debug_fields.py
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


async def _column_exists(conn: aiosqlite.Connection, column_name: str) -> bool:
    async with conn.execute("PRAGMA table_info(cards)") as cursor:
        columns = {row[1] async for row in cursor}
    return column_name in columns


async def migrate() -> None:
    db_path = settings.DATABASE_URL.removeprefix("sqlite+aiosqlite:///")
    logger.info("Connecting to %s", db_path)

    async with aiosqlite.connect(db_path) as conn:
        migrations = [
            ("final_prompt", "TEXT"),
            ("llm_model", "TEXT"),
            ("lora_used", "TEXT"),
            ("seed", "INTEGER"),
        ]

        changed = False
        for column_name, column_type in migrations:
            if await _column_exists(conn, column_name):
                logger.info("Column '%s' already exists ? skipping.", column_name)
                continue
            await conn.execute(f"ALTER TABLE cards ADD COLUMN {column_name} {column_type}")
            logger.info("Added column '%s' (%s).", column_name, column_type)
            changed = True

        if changed:
            await conn.commit()
            logger.info("Migration complete.")
        else:
            logger.info("No schema changes required.")


if __name__ == "__main__":
    asyncio.run(migrate())
