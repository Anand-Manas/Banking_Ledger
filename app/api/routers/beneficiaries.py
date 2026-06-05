from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session_async import get_async_db
from app.api.deps_async import require_customer_async
from app.models.beneficiary_model import Beneficiary
from app.models.customer_model import Customer
from app.models.account_model import Account
from app.services.audit_service_async import log_audit_async

router = APIRouter()

@router.post("/")
async def add_beneficiary(
    request: Request,
    beneficiary_account_number: str,
    bank_name: str,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.user_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # BLOCK: Cannot add your own account as beneficiary
    own_result = await db.execute(
        select(Account).where(
            Account.account_number == beneficiary_account_number,
            Account.customer_id == customer.customer_id
        )
    )
    if own_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add your own account as a beneficiary"
        )

    # BLOCK: Duplicate active beneficiary
    existing = await db.execute(
        select(Beneficiary).where(
            Beneficiary.customer_id == customer.customer_id,
            Beneficiary.beneficiary_account_number == beneficiary_account_number,
            Beneficiary.status == "ACTIVE"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Beneficiary already exists"
        )

    beneficiary = Beneficiary(
        customer_id=customer.customer_id,
        beneficiary_account_number=beneficiary_account_number,
        bank_name=bank_name,
    )
    db.add(beneficiary)
    await db.commit()
    await db.refresh(beneficiary)

    await log_audit_async(
        db, user.user_id, "BENEFICIARY_ADDED", "BENEFICIARY", beneficiary.beneficiary_id,
        ip_address=request.client.host
    )
    await db.commit()

    return {
        "beneficiary_id": str(beneficiary.beneficiary_id),
        "beneficiary_account_number": beneficiary.beneficiary_account_number,
        "bank_name": beneficiary.bank_name,
        "status": beneficiary.status,
    }

@router.get("/")
async def list_beneficiaries(
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.user_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    ben_result = await db.execute(
        select(Beneficiary).where(
            Beneficiary.customer_id == customer.customer_id,
            Beneficiary.status == "ACTIVE"
        )
    )
    beneficiaries = ben_result.scalars().all()

    return [
        {
            "beneficiary_id": str(b.beneficiary_id),
            "account_number": b.beneficiary_account_number,
            "bank_name": b.bank_name,
            "status": b.status,
        }
        for b in beneficiaries
    ]

@router.delete("/{beneficiary_id}")
async def remove_beneficiary(
    request: Request,
    beneficiary_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.user_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Ownership check
    ben_result = await db.execute(
        select(Beneficiary).where(
            Beneficiary.beneficiary_id == beneficiary_id,
            Beneficiary.customer_id == customer.customer_id
        )
    )
    beneficiary = ben_result.scalar_one_or_none()

    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )

    # Soft delete
    beneficiary.status = "INACTIVE"
    await db.commit()

    await log_audit_async(
        db, user.user_id, "BENEFICIARY_REMOVED", "BENEFICIARY", beneficiary_id,
        ip_address=request.client.host
    )
    await db.commit()

    return {
        "beneficiary_id": str(beneficiary.beneficiary_id),
        "status": "INACTIVE",
        "message": "Beneficiary removed successfully"
    }