"""HTML page routes - serves Jinja2 templates."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.card import Card
from app.models.card_config import CardConfig
from app.models.learning_record import LearningRecord
from app.models.student import Student
from app.models.unit import Unit
from app.services.scoring import get_available_options
from app.templating import templates

# Display labels for each unit's unlocked attribute
UNIT_ATTR_LABELS = {
    "unit_1": "種族 / 性別",
    "unit_2": "職業 / 體型",
    "unit_3": "服飾裝備",
    "unit_4": "武器",
    "unit_5": "背景場景",
    "unit_6": "表情 / 姿勢",
}

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    """Dashboard / home page."""
    user = request.state.user

    latest_card = None
    records_by_unit = {}

    if user:
        # Fetch latest card
        result = await db.execute(
            select(Card)
            .where(Card.student_id == user.id, Card.is_latest == True)
            .limit(1)
        )
        latest_card = result.scalar_one_or_none()

        # Fetch all units ordered by sort_order
        units_result = await db.execute(select(Unit).order_by(Unit.sort_order))
        units = units_result.scalars().all()

        # Fetch learning records for the user
        lr_result = await db.execute(
            select(LearningRecord)
            .where(LearningRecord.student_id == user.id)
            .options(selectinload(LearningRecord.unit))
        )
        learning_records = lr_result.scalars().all()
        records_by_unit = {lr.unit_id: lr for lr in learning_records}
    else:
        units_result = await db.execute(select(Unit).order_by(Unit.sort_order))
        units = units_result.scalars().all()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "user": user,
            "latest_card": latest_card,
            "units": units,
            "records_by_unit": records_by_unit,
        },
    )


@router.get("/cards", response_class=HTMLResponse)
async def cards_gallery(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Student = Depends(get_current_user),
):
    """My cards gallery page."""
    result = await db.execute(
        select(Card)
        .where(Card.student_id == user.id)
        .order_by(Card.created_at.desc())
    )
    cards = result.scalars().all()

    return templates.TemplateResponse(
        request, "cards/gallery.html", {"user": user, "cards": cards}
    )


@router.get("/cards/{card_id}", response_class=HTMLResponse)
async def card_detail(
    request: Request,
    card_id: int,
    db: AsyncSession = Depends(get_db),
    user: Student = Depends(get_current_user),
):
    """Single card detail page."""
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.student_id == user.id)
    )
    card = result.scalar_one_or_none()

    return templates.TemplateResponse(
        request, "cards/detail.html", {"user": user, "card": card}
    )


@router.get("/hall", response_class=HTMLResponse)
async def hall(request: Request, db: AsyncSession = Depends(get_db)):
    """Hall of heroes - all students' latest cards."""
    user = request.state.user

    result = await db.execute(
        select(Card)
        .where(Card.is_latest == True)
        .options(selectinload(Card.student))
        .order_by(Card.level_number.desc())
    )
    hero_cards = result.scalars().all()

    return templates.TemplateResponse(
        request, "hall.html", {"user": user, "hero_cards": hero_cards}
    )


@router.get("/progress", response_class=HTMLResponse)
async def progress(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Student = Depends(get_current_user),
):
    """My learning progress overview."""
    # Fetch all units
    units_result = await db.execute(select(Unit).order_by(Unit.sort_order))
    units = units_result.scalars().all()

    # Fetch learning records
    lr_result = await db.execute(
        select(LearningRecord)
        .where(LearningRecord.student_id == user.id)
        .options(selectinload(LearningRecord.unit))
    )
    learning_records = lr_result.scalars().all()
    records_by_unit = {lr.unit_id: lr for lr in learning_records}

    # Fetch card configs
    cc_result = await db.execute(
        select(CardConfig)
        .where(CardConfig.student_id == user.id)
        .options(selectinload(CardConfig.unit))
    )
    card_configs = cc_result.scalars().all()
    configs_by_unit = {}
    for cc in card_configs:
        configs_by_unit.setdefault(cc.unit_id, []).append(cc)

    # Build enriched unit data with scoring info
    unit_data = []
    for u in units:
        record = records_by_unit.get(u.id)
        configs = configs_by_unit.get(u.id, [])
        rate = record.completion_rate if record and record.completion_rate else 0

        # Determine status
        if record is None:
            status = "locked"
        elif rate >= 80:
            status = "completed"
        else:
            status = "in_progress"

        # Build chosen attributes display
        chosen_attrs = {c.attribute_type: c.attribute_value for c in configs}

        # Get available options from scoring engine
        available = {}
        if record and record.quiz_score is not None:
            available = await get_available_options(
                u.code,
                record.quiz_score,
                homework_score=record.homework_score,
                completion_rate=record.completion_rate,
                db=db,
            )

        unit_data.append({
            "unit": u,
            "record": record,
            "status": status,
            "rate": rate,
            "attr_label": UNIT_ATTR_LABELS.get(u.code, u.unlock_attribute),
            "chosen_attrs": chosen_attrs,
            "available": available,
        })

    return templates.TemplateResponse(
        request,
        "learning/progress.html",
        {
            "user": user,
            "unit_data": unit_data,
        },
    )


@router.get("/progress/{unit_code}", response_class=HTMLResponse)
async def unit_detail(
    request: Request,
    unit_code: str,
    db: AsyncSession = Depends(get_db),
    user: Student = Depends(get_current_user),
):
    """Single unit detail + attribute configuration."""
    # Fetch the unit
    unit_result = await db.execute(select(Unit).where(Unit.code == unit_code))
    unit = unit_result.scalar_one_or_none()

    if not unit:
        return templates.TemplateResponse(
            request, "learning/unit_detail.html",
            {"user": user, "unit": None, "record": None, "configs": [],
             "chosen_attrs": {}, "available": {}, "attr_label": ""},
        )

    # Fetch learning record for this unit
    lr_result = await db.execute(
        select(LearningRecord).where(
            LearningRecord.student_id == user.id,
            LearningRecord.unit_id == unit.id,
        )
    )
    record = lr_result.scalar_one_or_none()

    # Fetch card configs for this unit
    cc_result = await db.execute(
        select(CardConfig).where(
            CardConfig.student_id == user.id,
            CardConfig.unit_id == unit.id,
        )
    )
    configs = list(cc_result.scalars().all())
    chosen_attrs = {c.attribute_type: c.attribute_value for c in configs}

    # Get available options from scoring engine
    available = {}
    if record and record.quiz_score is not None:
        # For unit_4 (weapons), look up the student's chosen class
        character_class = None
        if unit_code == "unit_4":
            cls_result = await db.execute(
                select(CardConfig).where(
                    CardConfig.student_id == user.id,
                    CardConfig.attribute_type == "class",
                )
            )
            cls_config = cls_result.scalar_one_or_none()
            if cls_config:
                character_class = cls_config.attribute_value

        available = await get_available_options(
            unit_code,
            record.quiz_score,
            homework_score=record.homework_score,
            completion_rate=record.completion_rate,
            character_class=character_class,
            db=db,
        )

    return templates.TemplateResponse(
        request,
        "learning/unit_detail.html",
        {
            "user": user,
            "unit": unit,
            "record": record,
            "configs": configs,
            "chosen_attrs": chosen_attrs,
            "available": available,
            "attr_label": UNIT_ATTR_LABELS.get(unit_code, unit.unlock_attribute),
        },
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Self-registration page for unregistered users."""
    email = request.state.user_email
    return templates.TemplateResponse(
        request, "register.html", {"email": email}
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """Handle 2-step registration form.

    Step 1: look up student_id in the roster.
    Step 2: bind email + nickname to the roster student.
    """
    import re

    from fastapi.responses import RedirectResponse

    from app.services.auth import bind_student_email, get_roster_student

    email = request.state.user_email
    if not email:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"email": None, "error": "無法取得認證資訊"},
            status_code=400,
        )

    form = await request.form()
    step = form.get("step", "1")
    student_id = form.get("student_id", "").strip()

    if not student_id:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"email": email, "error": "請輸入學號"},
            status_code=400,
        )

    if step == "1":
        # Step 1: look up roster student
        result = await db.execute(
            select(Student).where(Student.student_id == student_id)
        )
        student = result.scalar_one_or_none()

        if student is None:
            return templates.TemplateResponse(
                request,
                "register.html",
                {"email": email, "error": "此學號不在修課名單中，請確認學號是否正確"},
                status_code=400,
            )

        # Check if already bound (real email, not placeholder)
        if not student.email.startswith("__unbound__"):
            return templates.TemplateResponse(
                request,
                "register.html",
                {"email": email, "error": "此學號已被註冊"},
                status_code=400,
            )

        # Show step 2: nickname entry
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "email": email,
                "roster_student": student,
            },
        )

    elif step == "2":
        # Step 2: bind email + nickname
        nickname = form.get("nickname", "").strip()

        if not nickname:
            # Re-fetch student for display
            roster_student = await get_roster_student(db, student_id)
            return templates.TemplateResponse(
                request,
                "register.html",
                {
                    "email": email,
                    "roster_student": roster_student,
                    "error": "請輸入角色暱稱",
                },
                status_code=400,
            )

        # Validate nickname: alphanumeric only, max 18 chars
        if not re.match(r'^[a-zA-Z0-9]+$', nickname) or len(nickname) > 18:
            roster_student = await get_roster_student(db, student_id)
            return templates.TemplateResponse(
                request,
                "register.html",
                {
                    "email": email,
                    "roster_student": roster_student,
                    "error": "暱稱僅限英數字，最多 18 字元",
                },
                status_code=400,
            )

        try:
            await bind_student_email(db, student_id, email, nickname)
        except ValueError:
            return templates.TemplateResponse(
                request,
                "register.html",
                {"email": email, "error": "綁定失敗，請重試"},
                status_code=400,
            )

        return RedirectResponse(url="/", status_code=302)
