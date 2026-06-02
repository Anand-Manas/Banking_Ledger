from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_admin
from app.schemas.admin_schemas import (
    CreateAdminRequest, CreateCustomerRequest, CreateAccountRequest, 
    CreditRequest, CustomerListItem, CustomerDetailResponse
)
from app.schemas.credit_request_schema import AdminCreditRequestAction
from app.services.admin_service import create_admin, create_customer, create_account, list_customers, get_customer_details
from app.services.credit_request_service import approve_credit_request, reject_credit_request, get_pending_credit_requests
from app.services.audit_service import log_audit
from app.repositories.account_repo import get_account_for_update
from decimal import Decimal

router = APIRouter()

@router.post("/admins")
def admin_create_admin(
    payload: CreateAdminRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    result = create_admin(db, payload)
    log_audit(db, admin.user_id, "ADMIN_CREATED", "USER", result["admin_id"])
    db.commit()
    return result

@router.get("/customers", response_model=list[CustomerListItem])
def admin_list_customers(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return list_customers(db)

@router.get("/customers/{customer_id}", response_model=CustomerDetailResponse)
def admin_get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return get_customer_details(db, customer_id)

@router.post("/customers")
def admin_create_customer(
    payload: CreateCustomerRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return create_customer(db, payload)

@router.post("/accounts")
def admin_create_account(
    payload: CreateAccountRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return create_account(db, payload)

@router.post("/credit")
def admin_credit_account(
    payload: CreditRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    account = get_account_for_update(db, payload.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.balance += Decimal(str(payload.amount))
    db.commit()
    return {"message": "Account credited", "new_balance": str(account.balance)}

@router.get("/credit-requests")
def admin_list_credit_requests(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return get_pending_credit_requests(db)

@router.post("/credit-requests/{request_id}/approve")
def admin_approve_credit_request(
    request_id: str,
    payload: AdminCreditRequestAction,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return approve_credit_request(db, request_id, admin.user_id, payload.admin_note)

@router.post("/credit-requests/{request_id}/reject")
def admin_reject_credit_request(
    request_id: str,
    payload: AdminCreditRequestAction,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return reject_credit_request(db, request_id, admin.user_id, payload.admin_note)
