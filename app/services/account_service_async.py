from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.account_model import Account
from app.utils.cache import get_cache, set_cache

ACCOUNTS_TTL = 120
ACCOUNT_TTL = 60

async def get_accounts_for_customer_async(db: AsyncSession, customer_id):
    cache_key = f"accounts:customer:{customer_id}"
    cached = get_cache(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Account).where(Account.customer_id == customer_id)
    )
    accounts = result.scalars().all()

    result_data = [
        {
            "account_id": str(a.account_id),
            "account_number": a.account_number,
            "account_type": a.account_type,
            "balance": str(a.balance),
            "status": a.status,
            "overdraft_limit": str(a.overdraft_limit),
        }
        for a in accounts
    ]

    set_cache(cache_key, result_data, ACCOUNTS_TTL)
    return result_data

async def get_account_for_customer_async(db: AsyncSession, customer_id, account_id):
    cache_key = f"account:{account_id}"
    cached = get_cache(cache_key)
    if cached and cached.get("customer_id") == str(customer_id):
        return cached

    result = await db.execute(
        select(Account).where(
            Account.account_id == account_id,
            Account.customer_id == customer_id
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    result_data = {
        "account_id": str(account.account_id),
        "customer_id": str(account.customer_id),
        "account_number": account.account_number,
        "account_type": account.account_type,
        "balance": str(account.balance),
        "status": account.status,
        "overdraft_limit": str(account.overdraft_limit),
    }

    set_cache(cache_key, result_data, ACCOUNT_TTL)
    return result_data