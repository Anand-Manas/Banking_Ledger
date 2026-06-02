from fastapi import HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from sqlalchemy.sql import func

from app.models.credit_request import CreditRequest
from app.models.account_model import Account
from app.models.customer_model import Customer
from app.services.audit_service import log_audit
from app.core.logging import logger


def create_credit_request(db: Session, customer_id, account_id, amount: Decimal, customer_note: str = None):
    account = db.query(Account).filter(
        Account.account_id == account_id,
        Account.customer_id == customer_id,
        Account.status == "ACTIVE"
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found or does not belong to customer")

    request = CreditRequest(
        customer_id=customer_id,
        account_id=account_id,
        amount=amount,
        status="PENDING",
        customer_note=customer_note,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    logger.info(f"Credit request created | customer={customer_id} | account={account_id} | amount={amount}")
    return request


def get_customer_credit_requests(db: Session, customer_id):
    requests = db.query(CreditRequest).filter(
        CreditRequest.customer_id == customer_id
    ).order_by(CreditRequest.requested_at.desc()).all()
    return requests


def get_pending_credit_requests(db: Session):
    results = db.query(
        CreditRequest,
        Customer.full_name,
        Account.account_number
    ).join(
        Customer, CreditRequest.customer_id == Customer.customer_id
    ).join(
        Account, CreditRequest.account_id == Account.account_id
    ).filter(
        CreditRequest.status == "PENDING"
    ).order_by(CreditRequest.requested_at.desc()).all()

    output = []
    for request, customer_name, account_number in results:
        output.append({
            "request_id": str(request.request_id),
            "customer_name": customer_name,
            "customer_id": str(request.customer_id),
            "account_number": account_number,
            "amount": str(request.amount),
            "customer_note": request.customer_note,
            "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        })
    return output


def approve_credit_request(db: Session, request_id: str, admin_user_id, admin_note: str = None):
    request = db.query(CreditRequest).filter(
        CreditRequest.request_id == request_id,
        CreditRequest.status == "PENDING"
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Credit request not found or already processed")

    account = db.query(Account).filter(
        Account.account_id == request.account_id
    ).with_for_update().first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.balance += request.amount
    request.status = "APPROVED"
    request.admin_note = admin_note
    request.processed_at = func.now()
    request.processed_by = admin_user_id

    db.commit()

    log_audit(
        db=db,
        user_id=admin_user_id,
        action="CREDIT_REQUEST_APPROVED",
        entity="CREDIT_REQUEST",
        entity_id=request.request_id
    )

    logger.info(f"Credit request approved | request={request_id} | admin={admin_user_id} | amount={request.amount}")
    return request


def reject_credit_request(db: Session, request_id: str, admin_user_id, admin_note: str = None):
    request = db.query(CreditRequest).filter(
        CreditRequest.request_id == request_id,
        CreditRequest.status == "PENDING"
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Credit request not found or already processed")

    request.status = "REJECTED"
    request.admin_note = admin_note
    request.processed_at = func.now()
    request.processed_by = admin_user_id

    db.commit()

    log_audit(
        db=db,
        user_id=admin_user_id,
        action="CREDIT_REQUEST_REJECTED",
        entity="CREDIT_REQUEST",
        entity_id=request.request_id
    )

    logger.info(f"Credit request rejected | request={request_id} | admin={admin_user_id}")
    return request
