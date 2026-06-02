from fastapi import HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.transaction_model import Transaction
from app.models.account_model import Account
from app.repositories.transaction_repo import get_by_idempotency
from app.repositories.account_repo import lock_accounts_in_order
from app.utils.cache import invalidate_cache
from app.services.audit_service import log_audit
from app.models.customer_model import Customer
from app.core.logging import logger

MAX_ALLOWED_AMOUNT = Decimal("999999999999.99")


def transfer_money(
    db: Session,
    customer_id,
    source_account_id,
    destination_account_number: str,
    amount: Decimal,
    idempotency_key: str,
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    if amount > MAX_ALLOWED_AMOUNT:
        raise HTTPException(
            status_code=400, 
            detail=f"Amount exceeds maximum limit of {MAX_ALLOWED_AMOUNT}"
        )

    # Look up destination account by account number
    destination_account = db.query(Account).filter(
        Account.account_number == destination_account_number,
        Account.status == "ACTIVE"
    ).first()

    if not destination_account:
        raise HTTPException(status_code=404, detail="Destination account not found")

    destination_account_id = destination_account.account_id

    if str(source_account_id) == str(destination_account_id):
        raise HTTPException(
            status_code=400, 
            detail="Source and destination accounts cannot be the same"
        )

    logger.info(
        f"Transfer initiated | customer={customer_id} | "
        f"source={source_account_id} | destination={destination_account_number} | "
        f"amount={amount}"
    )

    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    user_id = customer.user_id

    existing = get_by_idempotency(db, customer_id, idempotency_key)
    if existing:
        return existing

    try:
        txn = Transaction(
            customer_id=customer_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            transaction_type="TRANSFER",
            amount=amount,
            status="PENDING",
            idempotency_key=idempotency_key,
        )
        db.add(txn)
        db.flush()

        src, dst = lock_accounts_in_order(
            db, source_account_id, destination_account_id
        )

        if src.status != "ACTIVE" or dst.status != "ACTIVE":
            txn.status = "FAILED"
            log_audit(db, user_id, "TRANSFER_FAILED", "TRANSACTION", txn.transaction_id)
            db.commit()
            raise HTTPException(status_code=400, detail="One or both accounts are not active")

        projected = src.balance - amount
        if projected < -src.overdraft_limit:
            txn.status = "FAILED"
            log_audit(
                db=db,
                user_id=user_id, 
                action="TRANSFER_FAILED",
                entity="TRANSACTION",
                entity_id=txn.transaction_id
            )
            logger.warning(f"Transfer FAILED | overdraft exceeded | customer={customer_id}")
            db.commit()
            raise HTTPException(status_code=400, detail="Overdraft limit exceeded")

        src.balance -= amount
        dst.balance += amount
        txn.status = "SUCCESS"

        log_audit(
            db=db, 
            user_id=user_id, 
            action="TRANSFER_SUCCESS", 
            entity="TRANSACTION", 
            entity_id=txn.transaction_id
        )

        db.commit() 

        try:
            invalidate_cache(
                f"account:{src.account_id}",
                f"account:{dst.account_id}",
                f"accounts:customer:{customer_id}"
            )
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")

        return txn

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Critical Transfer Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Transfer Error")
