"""Seed the database with initial data (units).

Usage: uv run python scripts/seed_data.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.config import settings
from app.database import init_db, async_session
from app.models.unit import Unit


SEED_UNITS = [
    {
        "code": "unit_1",
        "name": "先備知識簡介",
        "description": "人工智慧基礎概念與先備知識",
        "week_start": 1,
        "week_end": 3,
        "unlock_attribute": "race_gender",
        "sort_order": 1,
    },
    {
        "code": "unit_2",
        "name": "多層感知器 (MLP)",
        "description": "多層感知器原理與實作",
        "week_start": 4,
        "week_end": 6,
        "unlock_attribute": "class_body",
        "sort_order": 2,
    },
    {
        "code": "unit_3",
        "name": "卷積神經網路 (CNN)",
        "description": "卷積神經網路原理與影像辨識",
        "week_start": 7,
        "week_end": 9,
        "unlock_attribute": "equipment",
        "sort_order": 3,
    },
    {
        "code": "unit_4",
        "name": "循環神經網路 (RNN/LSTM/GRU)",
        "description": "循環神經網路與序列資料處理",
        "week_start": 10,
        "week_end": 12,
        "unlock_attribute": "weapon",
        "sort_order": 4,
    },
    {
        "code": "unit_5",
        "name": "深度學習進階技術",
        "description": "深度學習進階技術與應用",
        "week_start": 13,
        "week_end": 16,
        "unlock_attribute": "background",
        "sort_order": 5,
    },
    {
        "code": "unit_6",
        "name": "自主學習",
        "description": "自主學習與課程回顧",
        "week_start": 17,
        "week_end": 18,
        "unlock_attribute": "expression_pose",
        "sort_order": 6,
    },
]


async def seed() -> None:
    # Ensure data directory exists
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create tables
    await init_db()
    print("Database tables created.")

    async with async_session() as session:
        for unit_data in SEED_UNITS:
            # Check if unit already exists (idempotent)
            result = await session.execute(
                select(Unit).where(Unit.code == unit_data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                # Update existing unit
                for key, value in unit_data.items():
                    setattr(existing, key, value)
                print(f"  Updated: {unit_data['code']} - {unit_data['name']}")
            else:
                session.add(Unit(**unit_data))
                print(f"  Inserted: {unit_data['code']} - {unit_data['name']}")

        await session.commit()

    print("Seed data complete.")


if __name__ == "__main__":
    asyncio.run(seed())
