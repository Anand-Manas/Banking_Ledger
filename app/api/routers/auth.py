from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session_async import get_async_db
from app.schemas.auth_schema import RegisterRequest
from app.services.auth_service_async import authenticate_user_async, register_customer_async

router = APIRouter()

@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    return await authenticate_user_async(
        db, form_data.username, form_data.password,
        ip_address=request.client.host
    )

@router.post("/register")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_async_db)
):
    return await register_customer_async(
        db, data,
        ip_address=request.client.host
    )