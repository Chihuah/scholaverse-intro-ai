"""Authentication service - Cloudflare Zero Trust header parsing + user lookup."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.student import Student
from app.models.token_transaction import TokenTransaction

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


async def get_user_by_email(db: AsyncSession, email: str) -> Student | None:
    """Look up a registered user by email."""
    result = await db.execute(select(Student).where(Student.email == email))
    return result.scalar_one_or_none()


async def create_student(
    db: AsyncSession, email: str, student_id: str, name: str
) -> Student:
    """Register a new student account."""
    student = Student(email=email, student_id=student_id, name=name, role="student")
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


async def get_roster_student(db: AsyncSession, student_id: str) -> Student | None:
    """Find an unbound roster student by student_id (placeholder email)."""
    result = await db.execute(
        select(Student).where(
            Student.student_id == student_id,
            Student.email.like("__unbound__%@placeholder"),
        )
    )
    return result.scalar_one_or_none()


async def bind_student_email(
    db: AsyncSession, student_id: str, email: str, nickname: str
) -> Student:
    """Bind a real email and nickname to a roster student."""
    student = await get_roster_student(db, student_id)
    if student is None:
        raise ValueError(f"No unbound roster student with id {student_id}")
    student.email = email
    student.nickname = nickname
    await db.commit()
    await db.refresh(student)
    return student


async def track_daily_login(db: AsyncSession, student: Student) -> bool:
    """Record the first login of each calendar day (Asia/Taipei) for any role.

    Sets ``last_login_date`` and ``last_login_at``. Students additionally get
    a 1-token daily login bonus (first time each day only).

    Returns True if this call triggered a first-of-day daily bonus for a
    student, False otherwise (already tracked today, or non-student role).
    """
    today = datetime.now(TAIPEI_TZ).date()
    fully_tracked = (
        student.last_login_date == today and student.last_login_at is not None
    )
    if fully_tracked:
        return False

    is_first_login_today = student.last_login_date != today

    student.last_login_date = today
    student.last_login_at = datetime.now(timezone.utc)

    awarded = False
    if is_first_login_today and student.role == "student":
        student.tokens += 1
        db.add(TokenTransaction(student_id=student.id, amount=1, reason="每日登入獎勵"))
        awarded = True

    await db.commit()
    await db.refresh(student)
    return awarded


def get_cf_email(headers: dict) -> str | None:
    """Extract authenticated email from Cloudflare Zero Trust header."""
    return headers.get(settings.CF_AUTH_HEADER)
