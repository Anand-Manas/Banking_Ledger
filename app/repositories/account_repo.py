from sqlalchemy.orm import Session
from app.models.account_model import Account
from uuid import UUID
from fastapi import HTTPException

def get_account_for_update(db: Session, account_id: str):
    return (
        db.query(Account)
        .filter(Account.account_id == account_id)
        .with_for_update()
        .first()
    )

def lock_accounts_in_order(db: Session, a_id, b_id):
    try:
        a_uuid = UUID(str(a_id))
        b_uuid = UUID(str(b_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account ID")

    first_id, second_id = sorted([a_uuid, b_uuid])

    accounts = (
        db.query(Account)
        .filter(Account.account_id.in_([first_id, second_id]))
        .with_for_update()
        .all()
    )

    if len(accounts) != 2:
        raise HTTPException(status_code=404, detail="One or both accounts not found")

    account_map = {acc.account_id: acc for acc in accounts}
    return account_map[a_uuid], account_map[b_uuid]
