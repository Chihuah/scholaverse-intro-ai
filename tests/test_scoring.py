from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


SCORING_PATH = (
    Path(__file__).resolve().parents[1] / "web_server" / "app" / "services" / "scoring.py"
)


def load_scoring_module():
    sqlalchemy = types.ModuleType("sqlalchemy")
    sqlalchemy.select = lambda *args, **kwargs: None
    ext = types.ModuleType("sqlalchemy.ext")
    asyncio_mod = types.ModuleType("sqlalchemy.ext.asyncio")

    class AsyncSession:
        pass

    asyncio_mod.AsyncSession = AsyncSession
    ext.asyncio = asyncio_mod
    sqlalchemy.ext = ext
    sys.modules.setdefault("sqlalchemy", sqlalchemy)
    sys.modules.setdefault("sqlalchemy.ext", ext)
    sys.modules.setdefault("sqlalchemy.ext.asyncio", asyncio_mod)

    spec = importlib.util.spec_from_file_location("web_scoring", SCORING_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_calculate_card_level_uses_common_rounding():
    scoring = load_scoring_module()

    assert scoring.calculate_card_level(0) == 1
    assert scoring.calculate_card_level(6) == 1
    assert scoring.calculate_card_level(7) == 1
    assert scoring.calculate_card_level(9) == 2
    assert scoring.calculate_card_level(15) == 3
    assert scoring.calculate_card_level(597) == 100
    assert scoring.calculate_card_level(600) == 100


def test_rarity_table_matches_course_progression():
    scoring = load_scoring_module()

    assert scoring.RARITY_TABLE == [
        (1, 10, {"N": 80, "R": 18, "SR": 2, "SSR": 0, "UR": 0}),
        (11, 20, {"N": 70, "R": 25, "SR": 5, "SSR": 0, "UR": 0}),
        (21, 30, {"N": 58, "R": 30, "SR": 10, "SSR": 2, "UR": 0}),
        (31, 40, {"N": 46, "R": 36, "SR": 15, "SSR": 3, "UR": 0}),
        (41, 50, {"N": 34, "R": 36, "SR": 22, "SSR": 7, "UR": 1}),
        (51, 60, {"N": 22, "R": 32, "SR": 28, "SSR": 14, "UR": 4}),
        (61, 70, {"N": 14, "R": 26, "SR": 32, "SSR": 22, "UR": 6}),
        (71, 80, {"N": 10, "R": 20, "SR": 34, "SSR": 26, "UR": 10}),
        (81, 90, {"N": 5, "R": 14, "SR": 28, "SSR": 36, "UR": 17}),
        (91, 100, {"N": 2, "R": 10, "SR": 22, "SSR": 40, "UR": 26}),
    ]
