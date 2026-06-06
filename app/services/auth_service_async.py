from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.repositories.user_repo_async import get_user_by_username_async
from app.core.security_async import verify_password, create_access_token, hash_password
from app.services.audit_service_async import log_audit_async
from app.core.logging import logger
from app.schemas.auth_schema import RegisterRequest
from app.models.user import User
from app.models.user_role import UserRole
from app.models.customer_model import Customer
from app.utils.password_validator import validate_password
from datetime import datetime, timezone

async def authenticate_user_async(db: AsyncSession, username: str, password: str, ip_address: str = None):
    user = await get_user_by_username_async(db, username)

    if not user or not verify_password(password, user.password_hash):
        logger.warning(f"Login FAILED | username={username} | ip={ip_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if user.status != "ACTIVE":
        logger.warning(f"Login FAILED | username={username} | ip={ip_address}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked"
        )

    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)

    token = create_access_token(data={"sub": str(user.user_id)})
    await log_audit_async(db, user.user_id, "LOGIN_SUCCESS", ip_address=ip_address)
    logger.info(f"Login success | user_id={user.user_id} | ip={ip_address}")
    return {"access_token": token, "token_type": "bearer"}

async def register_customer_async(db: AsyncSession, data: RegisterRequest, ip_address: str = None):
    existing = await get_user_by_username_async(db, data.username)
    if existing:
        raise HTTPException(400, "Username already exists")

    result = await db.execute(
        select(Customer).where(
            (Customer.email == data.email) | (Customer.phone == data.phone_number)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Email or Phone already registered")

    validate_password(data.password)

    try:
        new_user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            status="ACTIVE"
        )
        db.add(new_user)
        await db.flush()

        db.add(UserRole(user_id=new_user.user_id, role="CUSTOMER"))

        new_customer = Customer(
            user_id=new_user.user_id,
            full_name=data.full_name,
            email=data.email,
            phone=data.phone_number,
            customer_type=data.customer_type
        )
        db.add(new_customer)

        await log_audit_async(db, new_user.user_id, "REGISTER_SUCCESS", ip_address=ip_address)
        await db.commit()

        logger.info(f"Registration success | user={data.username} | ip={ip_address}")

        return {
            "message": "Registration successful",
            "customer_id": str(new_customer.customer_id)
        }

    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Database Integrity Error (Duplicate Data)")
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration Error: {str(e)}")
        raise HTTPException(500, "Internal Server Error")