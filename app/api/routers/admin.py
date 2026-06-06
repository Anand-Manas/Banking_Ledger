from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.db.session_async import get_async_db
from app.api.deps_async import require_admin_async
from app.schemas.admin_schemas import (
    CreateAdminRequest, CreateCustomerRequest, CreateAccountRequest,
    CreditRequest, CustomerListItem, CustomerDetailResponse
)
from app.schemas.credit_request_schema import AdminCreditRequestAction
from app.services.admin_service_async import (
    create_admin_async, create_customer_async, create_account_async,
    list_customers_async, get_customer_details_async,
    promote_customer_to_admin_async, list_admins_async
)
from app.services.credit_request_service_async import (
    approve_credit_request_async, reject_credit_request_async, get_pending_credit_requests_async
)
from app.services.audit_service_async import log_audit_async
from app.repositories.account_repo_async import get_account_for_update_async
from app.utils.cache import invalidate_cache  # ← ADD

router = APIRouter()

@router.post("/admins")
async def admin_create_admin(
    request: Request,
    payload: CreateAdminRequest,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    result = await create_admin_async(db, payload)
    await log_audit_async(
        db, admin.user_id, "ADMIN_CREATED", "USER", result["admin_id"],
        ip_address=request.client.host
    )
    await db.commit()
    return result

@router.get("/admins")
async def admin_list_admins(
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    """List all users with ADMIN role."""
    return await list_admins_async(db)

@router.post("/customers/{customer_id}/promote")
async def admin_promote_customer(
    request: Request,
    customer_id: str,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    """Promote an existing customer to admin."""
    result = await promote_customer_to_admin_async(db, customer_id)
    await log_audit_async(
        db, admin.user_id, "CUSTOMER_PROMOTED", "USER", result["user_id"],
        ip_address=request.client.host
    )
    await db.commit()
    return result

@router.get("/customers", response_model=list[CustomerListItem])
async def admin_list_customers(
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    return await list_customers_async(db)

@router.get("/customers/{customer_id}", response_model=CustomerDetailResponse)
async def admin_get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    return await get_customer_details_async(db, customer_id)

@router.post("/customers")
async def admin_create_customer(
    request: Request,
    payload: CreateCustomerRequest,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    result = await create_customer_async(db, payload)
    await log_audit_async(
        db, admin.user_id, "CUSTOMER_CREATED", "CUSTOMER", result["customer_id"],
        ip_address=request.client.host
    )
    await db.commit()
    return result

@router.post("/accounts")
async def admin_create_account(
    request: Request,
    payload: CreateAccountRequest,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    result = await create_account_async(db, payload)
    await log_audit_async(
        db, admin.user_id, "ACCOUNT_CREATED", "ACCOUNT", result["account_id"],
        ip_address=request.client.host
    )
    await db.commit()
    return result

@router.post("/credit")
async def admin_credit_account(
    request: Request,
    payload: CreditRequest,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    account = await get_account_for_update_async(db, str(payload.account_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.status == "FROZEN":
        raise HTTPException(status_code=400, detail="Account is frozen")
    if account.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Account is closed")

    account.balance += Decimal(str(payload.amount))
    await db.commit()

    invalidate_cache(f"account:{account.account_id}")  # ← ADD

    await log_audit_async(
        db, admin.user_id, "DIRECT_CREDIT", "ACCOUNT", account.account_id,
        ip_address=request.client.host
    )
    await db.commit()

    return {"message": "Account credited", "new_balance": str(account.balance)}

@router.get("/credit-requests")
async def admin_list_credit_requests(
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    return await get_pending_credit_requests_async(db)

@router.post("/credit-requests/{request_id}/approve")
async def admin_approve_credit_request(
    request: Request,
    request_id: str,
    payload: AdminCreditRequestAction,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    result = await approve_credit_request_async(db, request_id, str(admin.user_id), payload.admin_note)
    await log_audit_async(
        db, admin.user_id, "CREDIT_APPROVED", "CREDIT_REQUEST", request_id,
        ip_address=request.client.host
    )
    await db.commit()
    return result

@router.post("/credit-requests/{request_id}/reject")
async def admin_reject_credit_request(
    request: Request,
    request_id: str,
    payload: AdminCreditRequestAction,
    db: AsyncSession = Depends(get_async_db),
    admin=Depends(require_admin_async)
):
    result = await reject_credit_request_async(db, request_id, str(admin.user_id), payload.admin_note)
    await log_audit_async(
        db, admin.user_id, "CREDIT_REJECTED", "CREDIT_REQUEST", request_id,
        ip_address=request.client.host
    )
    await db.commit()
    return result