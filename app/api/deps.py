from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_role import UserRole

__all__ = ["get_current_user", "get_db", "require_admin", "require_customer"]

def _has_role(db: Session, user_id, role: str) -> bool:
    return db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role == role
    ).first() is not None

def require_admin(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _has_role(db, user.user_id, "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

def require_customer(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _has_role(db, user.user_id, "CUSTOMER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required"
        )
    return user
