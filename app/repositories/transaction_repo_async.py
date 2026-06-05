from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.transaction_model import Transaction

async def get_by_idempotency_async(db: AsyncSession, customer_id, key):
    result = await db.execute(
        select(Transaction).where(
            Transaction.customer_id == customer_id,
            Transaction.idempotency_key == key
        )
    )
    return result.scalar_one_or_none()

async def get_account_statement_async(db: AsyncSession, account_id: str, limit: int = 10):
    result = await db.execute(
        select(Transaction)
        .where(
            or_(
                Transaction.source_account_id == account_id,
                Transaction.destination_account_id == account_id
            )
        )
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()