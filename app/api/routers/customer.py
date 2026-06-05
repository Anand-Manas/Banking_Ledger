from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.db.session_async import get_async_db
from app.api.deps_async import require_customer_async, get_current_user_async
from app.services.account_service_async import get_accounts_for_customer_async, get_account_for_customer_async
from app.services.credit_request_service_async import create_credit_request_async, get_customer_credit_requests_async
from app.models.customer_model import Customer
from app.models.account_model import Account
from app.schemas.credit_request_schema import CustomerCreditRequestCreate
from app.services.audit_service_async import log_audit_async

router = APIRouter()

@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_async_db), user=Depends(get_current_user_async)):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return {
        "customer_id": str(customer.customer_id),
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
    }

@router.get("/accounts")
async def list_accounts(db: AsyncSession = Depends(get_async_db), user=Depends(require_customer_async)):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return await get_accounts_for_customer_async(db, customer.customer_id)

@router.get("/accounts/{account_id}")
async def get_account_detail(
    account_id: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return await get_account_for_customer_async(db, customer.customer_id, account_id)

@router.post("/credit-requests")
async def customer_create_credit_request(
    request: Request,
    payload: CustomerCreditRequestCreate,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    req = await create_credit_request_async(
        db=db,
        customer_id=customer.customer_id,
        account_id=payload.account_id,
        amount=Decimal(str(payload.amount)),
        customer_note=payload.customer_note
    )

    await log_audit_async(
        db, user.user_id, "CREDIT_REQUEST_CREATED", "CREDIT_REQUEST", req.request_id,
        ip_address=request.client.host
    )
    await db.commit()

    return {
        "request_id": str(req.request_id),
        "status": req.status,
        "amount": str(req.amount),
        "requested_at": req.requested_at.isoformat() if req.requested_at else None,
    }

@router.get("/credit-requests")
async def customer_list_credit_requests(
        db: AsyncSession = Depends(get_async_db),
        user=Depends(require_customer_async)
    ):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    requests = await get_customer_credit_requests_async(db, customer.customer_id)

    result_data = []
    for req in requests:
        acc_result = await db.execute(select(Account).where(Account.account_id == req.account_id))
        account = acc_result.scalar_one_or_none()
        result_data.append({
            "request_id": str(req.request_id),
            "account_number": account.account_number if account else "UNKNOWN",
            "amount": str(req.amount),
            "status": req.status,
            "customer_note": req.customer_note,
            "admin_note": req.admin_note,
            "requested_at": req.requested_at.isoformat() if req.requested_at else None,
            "processed_at": req.processed_at.isoformat() if req.processed_at else None,
        })
    return result_data