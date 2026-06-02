from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.transaction_model import Transaction

def get_by_idempotency(db: Session, customer_id, key):
    return (
        db.query(Transaction)
        .filter(
            Transaction.customer_id == customer_id,
            Transaction.idempotency_key == key
        )
        .first()
    )

def get_account_statement(db: Session, account_id: str, limit: int = 10):
    return (
        db.query(Transaction)
        .filter(
            or_(
                Transaction.source_account_id == account_id,
                Transaction.destination_account_id == account_id
            )
        )
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
