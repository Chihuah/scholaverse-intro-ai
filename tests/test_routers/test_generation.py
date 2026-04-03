"""Tests for POST /api/cards/generate — duplicate submission prevention (Fix 1).

Verifies:
1. First request succeeds and returns 200 with card_id / job_id.
2. Second concurrent request (pending/generating in-flight) returns 409.
3. Completed card does NOT block a new generation (is_regen path, token-gated).
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_config import CardConfig
from app.models.student import Student
from app.models.unit import Unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_student(db: AsyncSession) -> Student:
    """Insert a minimal student row and return it."""
    student = Student(
        student_id="411000001",
        name="Test Student",
        email="test@example.com",
        role="student",
        tokens=100,
        nickname="Tester",
    )
    db.add(student)
    await db.flush()
    return student


async def _seed_unit(db: AsyncSession, code: str = "unit_1") -> Unit:
    """Insert a minimal unit row."""
    unit = Unit(
        code=code,
        name="Test Unit",
        unlock_attribute="race",
    )
    db.add(unit)
    await db.flush()
    return unit


async def _seed_config(db: AsyncSession, student_id: int, unit_id: int) -> CardConfig:
    """Insert a minimal card config so the generate endpoint can proceed."""
    cfg = CardConfig(
        student_id=student_id,
        unit_id=unit_id,
        attribute_type="race",
        attribute_value="human",
        available_options=json.dumps(["human"]),
    )
    db.add(cfg)
    await db.flush()
    return cfg


async def _seed_card(
    db: AsyncSession, student_id: int, status: str
) -> Card:
    """Insert a card with the given status."""
    card = Card(
        student_id=student_id,
        config_snapshot="{}",
        status=status,
        border_style="bronze",
        level_number=1,
        is_latest=(status == "completed"),
    )
    db.add(card)
    await db.flush()
    return card


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cf_headers() -> dict[str, str]:
    return {"cf-access-authenticated-user-email": "test@example.com"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_first_time_succeeds(client, db_session, cf_headers):
    """First-time generation (no existing card) should return 200."""
    student = await _seed_student(db_session)
    unit = await _seed_unit(db_session)
    await _seed_config(db_session, student.id, unit.id)
    await db_session.commit()

    mock_job_id = "mock-job-123"
    with patch(
        "app.routers.generation.get_ai_worker_service"
    ) as mock_get_service:
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(return_value=mock_job_id)
        mock_get_service.return_value = mock_service

        resp = await client.post("/api/cards/generate", headers=cf_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "card_id" in body
    assert body["job_id"] == mock_job_id
    assert body["status"] == "generating"
    assert body["tokens_spent"] == 0


@pytest.mark.asyncio
async def test_generate_blocked_when_pending(client, db_session, cf_headers):
    """Should return 409 when a 'pending' card already exists."""
    student = await _seed_student(db_session)
    unit = await _seed_unit(db_session)
    await _seed_config(db_session, student.id, unit.id)
    await _seed_card(db_session, student.id, "pending")
    await db_session.commit()

    resp = await client.post("/api/cards/generate", headers=cf_headers)

    assert resp.status_code == 409, resp.text
    assert "生成中" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_generate_blocked_when_generating(client, db_session, cf_headers):
    """Should return 409 when a 'generating' card already exists."""
    student = await _seed_student(db_session)
    unit = await _seed_unit(db_session)
    await _seed_config(db_session, student.id, unit.id)
    await _seed_card(db_session, student.id, "generating")
    await db_session.commit()

    resp = await client.post("/api/cards/generate", headers=cf_headers)

    assert resp.status_code == 409, resp.text
    assert "生成中" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_generate_allowed_after_completed(client, db_session, cf_headers):
    """Completed card should NOT trigger 409 — proceeds to token check (is_regen path)."""
    student = await _seed_student(db_session)
    unit = await _seed_unit(db_session)
    await _seed_config(db_session, student.id, unit.id)
    await _seed_card(db_session, student.id, "completed")
    await db_session.commit()

    mock_job_id = "mock-job-456"
    with patch(
        "app.routers.generation.get_ai_worker_service"
    ) as mock_get_service:
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(return_value=mock_job_id)
        mock_get_service.return_value = mock_service

        resp = await client.post("/api/cards/generate", headers=cf_headers)

    # 200 expected (student has 100 tokens, cost is 5)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tokens_spent"] == 5


@pytest.mark.asyncio
async def test_generate_blocked_when_failed_card_and_new_pending(client, db_session, cf_headers):
    """A failed card plus a pending card — the pending should still block."""
    student = await _seed_student(db_session)
    unit = await _seed_unit(db_session)
    await _seed_config(db_session, student.id, unit.id)
    await _seed_card(db_session, student.id, "failed")
    await _seed_card(db_session, student.id, "pending")
    await db_session.commit()

    resp = await client.post("/api/cards/generate", headers=cf_headers)

    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# Fix 3B tests: job_id persistence + card_status endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_persists_job_id(client, db_session, cf_headers):
    """job_id returned by ai-worker must be stored on the Card row."""
    from sqlalchemy import select
    from app.models.card import Card

    student = await _seed_student(db_session)
    unit = await _seed_unit(db_session)
    await _seed_config(db_session, student.id, unit.id)
    await db_session.commit()

    mock_job_id = "persist-job-xyz"
    with patch("app.routers.generation.get_ai_worker_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(return_value=mock_job_id)
        mock_get_service.return_value = mock_service

        resp = await client.post("/api/cards/generate", headers=cf_headers)

    assert resp.status_code == 200, resp.text
    card_id = resp.json()["card_id"]

    # Reload the Card from DB and verify job_id was stored
    await db_session.rollback()  # see latest committed state
    result = await db_session.execute(select(Card).where(Card.id == card_id))
    card = result.scalar_one()
    assert card.job_id == mock_job_id


@pytest.mark.asyncio
async def test_card_status_returns_basic_fields(client, db_session, cf_headers):
    """GET /api/cards/{id}/status should return status, image_url, thumbnail_url."""
    student = await _seed_student(db_session)
    card = await _seed_card(db_session, student.id, "completed")
    card.image_url = "http://example.com/card.png"
    card.thumbnail_url = "http://example.com/card_thumb.png"
    await db_session.commit()

    resp = await client.get(f"/api/cards/{card.id}/status", headers=cf_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["card_id"] == card.id
    assert body["status"] == "completed"
    assert body["image_url"] == "http://example.com/card.png"
    assert body["thumbnail_url"] == "http://example.com/card_thumb.png"


@pytest.mark.asyncio
async def test_card_status_not_found_for_other_student(client, db_session, cf_headers):
    """A student must not be able to see another student's card status."""
    # Seed the card owner (different student)
    owner = Student(
        student_id="411999999",
        name="Other Student",
        email="other@example.com",
        role="student",
        tokens=100,
    )
    db_session.add(owner)
    await db_session.flush()
    card = await _seed_card(db_session, owner.id, "completed")
    # Seed the requesting student (test@example.com via cf_headers)
    await _seed_student(db_session)
    await db_session.commit()

    resp = await client.get(f"/api/cards/{card.id}/status", headers=cf_headers)

    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_card_status_generating_includes_queue_position(client, db_session, cf_headers):
    """card_status with a 'generating' card should include queue_position from ai-worker."""
    from app.models.card import Card

    student = await _seed_student(db_session)
    card = Card(
        student_id=student.id,
        config_snapshot="{}",
        status="generating",
        job_id="live-job-001",
        border_style="bronze",
        level_number=1,
        is_latest=True,
    )
    db_session.add(card)
    await db_session.commit()

    mock_job_info = {"status": "generating", "position": 2, "estimated_seconds": 60}
    with patch("app.routers.generation.get_ai_worker_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.check_job_status = AsyncMock(return_value=mock_job_info)
        mock_get_service.return_value = mock_service

        resp = await client.get(f"/api/cards/{card.id}/status", headers=cf_headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "generating"
    assert body["queue_position"] == 2
    assert body["estimated_seconds"] == 60


@pytest.mark.asyncio
async def test_card_status_generating_no_job_id_skips_poll(client, db_session, cf_headers):
    """If card is generating but has no job_id, ai-worker poll must be skipped."""
    student = await _seed_student(db_session)
    card = await _seed_card(db_session, student.id, "generating")
    # job_id intentionally left None
    await db_session.commit()

    with patch("app.routers.generation.get_ai_worker_service") as mock_get_service:
        mock_service = MagicMock()
        mock_service.check_job_status = AsyncMock(return_value={"status": "not_found"})
        mock_get_service.return_value = mock_service

        resp = await client.get(f"/api/cards/{card.id}/status", headers=cf_headers)

        # check_job_status must NOT have been called
        mock_service.check_job_status.assert_not_called()

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "generating"
