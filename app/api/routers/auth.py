from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth_schema import LoginRequest, RegisterRequest
from app.services.auth_service import authenticate_user, register_customer

router = APIRouter()

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return authenticate_user(db, data.username, data.password)

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return register_customer(db, data)
