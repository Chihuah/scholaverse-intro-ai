"""Seed the attribute_rules table from scoring.py constants.

Usage: uv run python scripts/seed_attribute_rules.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.config import settings
from app.database import init_db, async_session
from app.models.attribute_rule import AttributeRule
from app.services.scoring import (
    RACE_OPTIONS, RACE_LABELS,
    GENDER_OPTIONS, GENDER_LABELS,
    CLASS_OPTIONS, CLASS_LABELS,
    BODY_OPTIONS, BODY_LABELS,
    EQUIPMENT_OPTIONS, EQUIPMENT_LABELS,
    WEAPON_QUALITY, WEAPON_QUALITY_LABELS,
    WEAPON_TYPES_BY_TIER, WEAPON_TYPE_LABELS,
    BACKGROUND_OPTIONS, BACKGROUND_LABELS,
    EXPRESSION_OPTIONS, EXPRESSION_LABELS,
    POSE_OPTIONS, POSE_LABELS,
)

TIERS = ["S", "A", "B", "C", "D"]

# Mapping: (unit_code, attribute_type, options_source, labels_source, sort_order)
RULE_DEFS: list[dict] = []


def _add_tiered(unit_code: str, attribute_type: str, options_map: dict[str, list[str]],
                labels_map: dict[str, str], sort_order: int):
    """Add rules for a standard tiered options map."""
    for tier in TIERS:
        opts = options_map[tier]
        RULE_DEFS.append({
            "unit_code": unit_code,
            "attribute_type": attribute_type,
            "tier": tier,
            "options": json.dumps(opts),
            "labels": json.dumps({k: labels_map[k] for k in opts}, ensure_ascii=False),
            "sort_order": sort_order,
        })


# Unit 1: race
_add_tiered("unit_1", "race", RACE_OPTIONS, RACE_LABELS, 1)

# Unit 1: gender (same options for all tiers)
for tier in TIERS:
    RULE_DEFS.append({
        "unit_code": "unit_1",
        "attribute_type": "gender",
        "tier": tier,
        "options": json.dumps(GENDER_OPTIONS),
        "labels": json.dumps(GENDER_LABELS, ensure_ascii=False),
        "sort_order": 2,
    })

# Unit 2: class, body
_add_tiered("unit_2", "class", CLASS_OPTIONS, CLASS_LABELS, 1)
_add_tiered("unit_2", "body", BODY_OPTIONS, BODY_LABELS, 2)

# Unit 3: equipment
_add_tiered("unit_3", "equipment", EQUIPMENT_OPTIONS, EQUIPMENT_LABELS, 1)

# Unit 4: weapon_quality (single value per tier)
for tier in TIERS:
    quality = WEAPON_QUALITY[tier]
    RULE_DEFS.append({
        "unit_code": "unit_4",
        "attribute_type": "weapon_quality",
        "tier": tier,
        "options": json.dumps([quality]),
        "labels": json.dumps({quality: WEAPON_QUALITY_LABELS[quality]}, ensure_ascii=False),
        "sort_order": 1,
    })

# Unit 4: weapon_type
_add_tiered("unit_4", "weapon_type", WEAPON_TYPES_BY_TIER, WEAPON_TYPE_LABELS, 2)

# Unit 5: background
_add_tiered("unit_5", "background", BACKGROUND_OPTIONS, BACKGROUND_LABELS, 1)

# Unit 6: expression, pose
_add_tiered("unit_6", "expression", EXPRESSION_OPTIONS, EXPRESSION_LABELS, 1)
_add_tiered("unit_6", "pose", POSE_OPTIONS, POSE_LABELS, 2)


async def seed() -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    print("Database tables created/verified.")

    async with async_session() as session:
        created = 0
        updated = 0
        for rule_data in RULE_DEFS:
            result = await session.execute(
                select(AttributeRule).where(
                    AttributeRule.unit_code == rule_data["unit_code"],
                    AttributeRule.attribute_type == rule_data["attribute_type"],
                    AttributeRule.tier == rule_data["tier"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                for key, value in rule_data.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                session.add(AttributeRule(**rule_data))
                created += 1

        await session.commit()

    print(f"Seed complete: {created} created, {updated} updated, {created + updated} total.")


if __name__ == "__main__":
    asyncio.run(seed())
