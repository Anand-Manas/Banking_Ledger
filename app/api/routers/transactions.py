from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import require_customer, get_current_user
from app.schemas.transaction_schema import TransferRequest
from app.services.transaction_service import transfer_money
from app.repositories.transaction_repo import get_account_statement
from app.models.customer_model import Customer
from app.models.account_model import Account

router = APIRouter()

@router.post("/transfer")
def create_transfer(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # CRITICAL: Verify the source account belongs to this customer
    source_account = db.query(Account).filter(
        Account.account_id == payload.source_account_id,
        Account.customer_id == customer.customer_id,
        Account.status == "ACTIVE"
    ).first()

    if not source_account:
        raise HTTPException(
            status_code=403,
            detail="Source account not found or does not belong to you"
        )

    txn = transfer_money(
        db=db,
        customer_id=customer.customer_id,
        source_account_id=payload.source_account_id,
        destination_account_number=payload.destination_account_number,
        amount=Decimal(str(payload.amount)),
        idempotency_key=payload.idempotency_key,
    )
    return {
        "transaction_id": str(txn.transaction_id),
        "status": txn.status,
        "amount": str(txn.amount),
    }

@router.get("/statement/{account_id}")
def get_statement(
    account_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    account = db.query(Account).filter(
        Account.account_id == account_id,
        Account.customer_id == customer.customer_id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    transactions = get_account_statement(db, account_id, limit)
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