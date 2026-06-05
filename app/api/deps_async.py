from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session_async import get_async_db
from app.core.security_async import get_current_user_async
from app.models.user import User
from app.models.user_role import UserRole

__all__ = ["get_current_user_async", "get_async_db", "require_admin_async", "require_customer_async"]

async def _has_role(db: AsyncSession, user_id, role: str) -> bool:
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role == role
        )
    )
    return result.scalar_one_or_none() is not None

async def require_admin_async(
    user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    if not await _has_role(db, user.user_id, "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def require_customer_async(
    user: User = Depends(get_current_user_async),
    db: AsyncSession = Depends(get_async_db)
):
    if not await _has_role(db, user.user_id, "CUSTOMER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required"
        )
    return user