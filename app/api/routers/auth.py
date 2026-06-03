from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth_schema import RegisterRequest
from app.services.auth_service import authenticate_user, register_customer

router = APIRouter()

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    return authenticate_user(db, form_data.username, form_data.password)

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return register_customer(db, data)