from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from sqlalchemy.sql import func

from app.models.credit_request import CreditRequest
from app.models.account_model import Account
from app.models.customer_model import Customer
from app.services.audit_service_async import log_audit_async
from app.core.logging import logger
from app.utils.cache import invalidate_cache  # ← ADD

async def create_credit_request_async(db: AsyncSession, customer_id, account_id, amount: Decimal, customer_note: str = None):
    result = await db.execute(
        select(Account).where(
            Account.account_id == account_id,
            Account.customer_id == customer_id,
            Account.status == "ACTIVE"
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found or does not belong to customer")

    request = CreditRequest(
        customer_id=customer_id,
        account_id=account_id,
        amount=amount,
        status="PENDING",
        customer_note=customer_note,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)

    logger.info(f"Credit request created | customer={customer_id} | account={account_id} | amount={amount}")
    return request

async def get_customer_credit_requests_async(db: AsyncSession, customer_id):
    result = await db.execute(
        select(CreditRequest)
        .where(CreditRequest.customer_id == customer_id)
        .order_by(CreditRequest.requested_at.desc())
    )
    return result.scalars().all()

async def get_pending_credit_requests_async(db: AsyncSession):
    result = await db.execute(
        select(CreditRequest, Customer.full_name, Account.account_number)
        .join(Customer, CreditRequest.customer_id == Customer.customer_id)
        .join(Account, CreditRequest.account_id == Account.account_id)
        .where(CreditRequest.status == "PENDING")
        .order_by(CreditRequest.requested_at.desc())
    )
    results = result.all()

    output = []
    for request, customer_name, account_number in results:
        output.append({
            "request_id": str(request.request_id),
            "customer_name": customer_name,
            "customer_id": str(request.customer_id),
            "account_number": account_number,
            "amount": str(request.amount),
            "status": request.status,  # ← ADD
            "customer_note": request.customer_note,
            "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        })
    return output

async def approve_credit_request_async(db: AsyncSession, request_id: str, admin_user_id, admin_note: str = None):
    result = await db.execute(
        select(CreditRequest).where(
            CreditRequest.request_id == request_id,
            CreditRequest.status == "PENDING"
        )
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Credit request not found or already processed")

    acc_result = await db.execute(
        select(Account).where(Account.account_id == request.account_id).with_for_update()
    )
    account = acc_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.balance += request.amount
    request.status = "APPROVED"
    request.admin_note = admin_note
    request.processed_at = func.now()
    request.processed_by = admin_user_id

    await db.commit()

    # FIX: Invalidate cache so subsequent reads get the new balance
    invalidate_cache(f"account:{account.account_id}")  # ← ADD

    await log_audit_async(
        db=db, user_id=admin_user_id,
        action="CREDIT_REQUEST_APPROVED",
        entity="CREDIT_REQUEST", entity_id=request.request_id
    )

    logger.info(f"Credit request approved | request={request_id} | admin={admin_user_id} | amount={request.amount}")
    return request

async def reject_credit_request_async(db: AsyncSession, request_id: str, admin_user_id, admin_note: str = None):
    result = await db.execute(
        select(CreditRequest).where(
            CreditRequest.request_id == request_id,
            CreditRequest.status == "PENDING"
        )
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Credit request not found or already processed")

    request.status = "REJECTED"
    request.admin_note = admin_note
    request.processed_at = func.now()
    request.processed_by = admin_user_id

    await db.commit()

    await log_audit_async(
        db=db, user_id=admin_user_id,
        action="CREDIT_REQUEST_REJECTED",
        entity="CREDIT_REQUEST", entity_id=request.request_id
    )

    logger.info(f"Credit request rejected | request={request_id} | admin={admin_user_id}")
    return request