"""Authentication service - Cloudflare Zero Trust header parsing + user lookup."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.student import Student


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


def get_cf_email(headers: dict) -> str | None:
    """Extract authenticated email from Cloudflare Zero Trust header."""
    return headers.get(settings.CF_AUTH_HEADER)
