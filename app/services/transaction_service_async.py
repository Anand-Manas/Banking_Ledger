from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from app.models.transaction_model import Transaction
from app.models.account_model import Account
from app.models.customer_model import Customer
from app.repositories.transaction_repo_async import get_by_idempotency_async
from app.repositories.account_repo_async import lock_accounts_in_order_async
from app.utils.cache import invalidate_cache
from app.services.audit_service_async import log_audit_async
from app.core.logging import logger

MAX_ALLOWED_AMOUNT = Decimal("999999999999.99")


async def transfer_money_async(
    db: AsyncSession,
    customer_id,
    source_account_id,
    destination_account_number: str,
    amount: Decimal,
    idempotency_key: str,
    ip_address: str = None,
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    if amount > MAX_ALLOWED_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds maximum limit of {MAX_ALLOWED_AMOUNT}"
        )

    # 1. Resolve destination by account number (regular SELECT — no lock yet)
    result = await db.execute(
        select(Account).where(
            Account.account_number == destination_account_number,
            Account.status == "ACTIVE"
        )
    )
    destination_account = result.scalar_one_or_none()

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
        f"amount={amount} | ip={ip_address}"
    )

    # 2. Resolve customer for audit
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    user_id = customer.user_id

    # 3. Idempotency check
    existing = await get_by_idempotency_async(db, customer_id, idempotency_key)
    if existing:
        return existing

    src, dst = await lock_accounts_in_order_async(
        db, source_account_id, destination_account_id
    )

    # 4. Create transaction row AFTER accounts are locked
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
    await db.flush()

    # 5. Business rule checks (on the locked rows — no race conditions possible)
    if src.status == "FROZEN":
        txn.status = "FAILED"
        await log_audit_async(db, user_id, "TRANSFER_FAILED", "TRANSACTION", txn.transaction_id, ip_address)
        await db.commit()
        raise HTTPException(status_code=400, detail="Source account is frozen")
    if src.status == "CLOSED":
        txn.status = "FAILED"
        await log_audit_async(db, user_id, "TRANSFER_FAILED", "TRANSACTION", txn.transaction_id, ip_address)
        await db.commit()
        raise HTTPException(status_code=400, detail="Source account is closed")
    if dst.status == "FROZEN":
        txn.status = "FAILED"
        await log_audit_async(db, user_id, "TRANSFER_FAILED", "TRANSACTION", txn.transaction_id, ip_address)
        await db.commit()
        raise HTTPException(status_code=400, detail="Destination account is frozen")
    if dst.status == "CLOSED":
        txn.status = "FAILED"
        await log_audit_async(db, user_id, "TRANSFER_FAILED", "TRANSACTION", txn.transaction_id, ip_address)
        await db.commit()
        raise HTTPException(status_code=400, detail="Destination account is closed")

    if src.min_balance > 0 and (src.balance - amount) < src.min_balance:
        txn.status = "FAILED"
        await log_audit_async(
            db=db, user_id=user_id, action="TRANSFER_FAILED",
            entity="TRANSACTION", entity_id=txn.transaction_id, ip_address=ip_address
        )
        logger.warning(f"Transfer FAILED | min_balance violated | customer={customer_id}")
        await db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Minimum balance of {src.min_balance} must be maintained"
        )

    projected = src.balance - amount
    if projected < -src.overdraft_limit:
        txn.status = "FAILED"
        await log_audit_async(
            db=db, user_id=user_id, action="TRANSFER_FAILED",
            entity="TRANSACTION", entity_id=txn.transaction_id, ip_address=ip_address
        )
        logger.warning(f"Transfer FAILED | overdraft exceeded | customer={customer_id}")
        await db.commit()
        raise HTTPException(status_code=400, detail="Overdraft limit exceeded")

    # 6. Execute transfer
    src.balance -= amount
    dst.balance += amount
    txn.status = "SUCCESS"

    await log_audit_async(
        db=db, user_id=user_id, action="TRANSFER_SUCCESS",
        entity="TRANSACTION", entity_id=txn.transaction_id, ip_address=ip_address
    )

    await db.commit()

    # 7. Cache invalidation (fire-and-forget, non-blocking)
    try:
        invalidate_cache(
            f"account:{src.account_id}",
            f"account:{dst.account_id}",
            f"accounts:customer:{customer_id}"
        )
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")

    return txn