"""FastAPI dependencies for route handlers."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.student import Student
from app.services.auth import get_user_by_email


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> Student:
    """Require an authenticated and registered user. Returns Student."""
    email = request.state.user_email
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=403, detail="Not registered")
    return user


async def require_teacher(user: Student = Depends(get_current_user)) -> Student:
    """Require teacher or admin role."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user


async def require_admin(user: Student = Depends(get_current_user)) -> Student:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
