"""Token management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.student import Student
from app.models.token_transaction import TokenTransaction

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


class SpendRequest(BaseModel):
    amount: int
    reason: str


class SpendResponse(BaseModel):
    ok: bool
    remaining_tokens: int
    transaction_id: int


class TransactionItem(BaseModel):
    id: int
    amount: int
    reason: str | None
    created_at: str


@router.post("/spend", response_model=SpendResponse)
async def spend_tokens(
    body: SpendRequest,
    user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deduct tokens from the user's balance."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if user.tokens < body.amount:
        raise HTTPException(
            status_code=400,
            detail=f"代幣不足（需要 {body.amount}，餘額 {user.tokens}）",
        )

    user.tokens -= body.amount

    txn = TokenTransaction(
        student_id=user.id,
        amount=-body.amount,
        reason=body.reason,
    )
    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    return SpendResponse(
        ok=True,
        remaining_tokens=user.tokens,
        transaction_id=txn.id,
    )


@router.get("/history", response_model=list[TransactionItem])
async def token_history(
    user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return user's token transaction history."""
    result = await db.execute(
        select(TokenTransaction)
        .where(TokenTransaction.student_id == user.id)
        .order_by(TokenTransaction.created_at.desc())
    )
    txns = result.scalars().all()

    return [
        TransactionItem(
            id=t.id,
            amount=t.amount,
            reason=t.reason,
            created_at=t.created_at.isoformat(),
        )
        for t in txns
    ]
