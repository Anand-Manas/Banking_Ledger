from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.account_model import Account
from uuid import UUID
from fastapi import HTTPException

async def get_account_for_update_async(db: AsyncSession, account_id: str):
    result = await db.execute(
        select(Account)
        .where(Account.account_id == account_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()

async def lock_accounts_in_order_async(db: AsyncSession, a_id, b_id):
    try:
        a_uuid = UUID(str(a_id))
        b_uuid = UUID(str(b_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account ID")

    first_id, second_id = sorted([a_uuid, b_uuid])

    result1 = await db.execute(
        select(Account).where(Account.account_id == first_id).with_for_update()
    )
    acc1 = result1.scalar_one_or_none()

    result2 = await db.execute(
        select(Account).where(Account.account_id == second_id).with_for_update()
    )
    acc2 = result2.scalar_one_or_none()

    if acc1 is None or acc2 is None:
        raise HTTPException(status_code=404, detail="One or both accounts not found")

    account_map = {acc1.account_id: acc1, acc2.account_id: acc2}
    return account_map[a_uuid], account_map[b_uuid]