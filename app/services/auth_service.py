from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repo import get_user_by_username
from app.core.security import verify_password, create_access_token, hash_password
from app.services.audit_service import log_audit
from app.core.logging import logger
from app.schemas.auth_schema import RegisterRequest
from app.models.user import User
from app.models.user_role import UserRole
from app.models.customer_model import Customer
from app.utils.password_validator import validate_password


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)

    if not user or not verify_password(password, user.password_hash):
        logger.warning(f"Login FAILED | username={username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if user.status != "ACTIVE":
        logger.warning(f"Login FAILED | username={username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked"
        )

    token = create_access_token(
        data={"sub": str(user.user_id)}
    )
    log_audit(
        db=db,
        user_id=user.user_id,
        action="LOGIN_SUCCESS",
    )
    logger.info(f"Login success | user_id={user.user_id}")
    return {"access_token": token, "token_type": "bearer"}

def register_customer(db: Session, data: RegisterRequest):
    if get_user_by_username(db, data.username):
        raise HTTPException(400, "Username already exists")

    if db.query(Customer).filter(
        (Customer.email == data.email) | (Customer.phone == data.phone_number)
    ).first():
        raise HTTPException(400, "Email or Phone already registered")

    validate_password(data.password)

    try:
        new_user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            status="ACTIVE"
        )
        db.add(new_user)
        db.flush()

        db.add(UserRole(user_id=new_user.user_id, role="CUSTOMER"))

        new_customer = Customer(
            user_id=new_user.user_id,
            full_name=data.full_name,
            email=data.email,
            phone=data.phone_number,
            customer_type=data.customer_type
        )
        db.add(new_customer)

        log_audit(db, new_user.user_id, "REGISTER_SUCCESS")
        db.commit()

        logger.info(f"Registration success | user={data.username}")

        return {
            "message": "Registration successful",
            "customer_id": str(new_customer.customer_id)
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Database Integrity Error (Duplicate Data)")
    except Exception as e:
        db.rollback()
        logger.error(f"Registration Error: {str(e)}")
        raise HTTPException(500, "Internal Server Error")
