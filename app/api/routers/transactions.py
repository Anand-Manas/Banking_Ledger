from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from sqlalchemy import select

from app.db.session_async import get_async_db
from app.api.deps_async import require_customer_async, get_current_user_async
from app.schemas.transaction_schema import TransferRequest
from app.services.transaction_service_async import transfer_money_async
from app.repositories.transaction_repo_async import get_account_statement_async
from app.models.customer_model import Customer
from app.models.account_model import Account

router = APIRouter()

@router.post("/transfer")
async def create_transfer(
    request: Request,
    payload: TransferRequest,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = await db.execute(
        select(Account).where(
            Account.account_id == str(payload.source_account_id),
            Account.customer_id == customer.customer_id,
            Account.status == "ACTIVE"
        )
    )
    source_account = result.scalar_one_or_none()

    if not source_account:
        raise HTTPException(
            status_code=403,
            detail="Source account not found or does not belong to you"
        )

    txn = await transfer_money_async(
        db=db,
        customer_id=customer.customer_id,
        source_account_id=payload.source_account_id,
        destination_account_number=payload.destination_account_number,
        amount=Decimal(str(payload.amount)),
        idempotency_key=payload.idempotency_key,
        ip_address=request.client.host,
    )
    return {
        "transaction_id": str(txn.transaction_id),
        "status": txn.status,
        "amount": str(txn.amount),
    }

@router.get("/statement/{account_id}")
async def get_statement(
    account_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(require_customer_async)
):
    result = await db.execute(select(Customer).where(Customer.user_id == user.user_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = await db.execute(
        select(Account).where(
            Account.account_id == account_id,
            Account.customer_id == customer.customer_id
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    transactions = await get_account_statement_async(db, account_id, limit)
    return {
        "account_id": account_id,
        "current_balance": str(account.balance),
        "transactions": [
            {
                "transaction_id": str(t.transaction_id),
                "type": t.transaction_type,
                "amount": str(t.amount),
                "status": t.status,
                "timestamp": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ]
    }