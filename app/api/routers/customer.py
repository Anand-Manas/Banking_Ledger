from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_customer, get_current_user
from app.services.account_service import get_accounts_for_customer, get_account_for_customer
from app.services.credit_request_service import create_credit_request, get_customer_credit_requests
from app.models.customer_model import Customer
from app.schemas.credit_request_schema import CustomerCreditRequestCreate

router = APIRouter()

@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user=Depends(get_current_user)):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return {
        "customer_id": str(customer.customer_id),
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
    }

@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), user=Depends(require_customer)):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return get_accounts_for_customer(db, customer.customer_id)

@router.get("/accounts/{account_id}")
def get_account_detail(
    account_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return get_account_for_customer(db, customer.customer_id, account_id)

@router.post("/credit-requests")
def customer_create_credit_request(
    payload: CustomerCreditRequestCreate,
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    from decimal import Decimal
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    request = create_credit_request(
        db=db,
        customer_id=customer.customer_id,
        account_id=payload.account_id,
        amount=Decimal(str(payload.amount)),
        customer_note=payload.customer_note
    )

    return {
        "request_id": str(request.request_id),
        "status": request.status,
        "amount": str(request.amount),
        "requested_at": request.requested_at.isoformat() if request.requested_at else None,
    }

@router.get("/credit-requests")
def customer_list_credit_requests(
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    requests = get_customer_credit_requests(db, customer.customer_id)

    result = []
    for req in requests:
        account = db.query(Account).filter(Account.account_id == req.account_id).first()
        result.append({
            "request_id": str(req.request_id),
            "account_number": account.account_number if account else "UNKNOWN",
            "amount": str(req.amount),
            "status": req.status,
            "customer_note": req.customer_note,
            "admin_note": req.admin_note,
            "requested_at": req.requested_at.isoformat() if req.requested_at else None,
            "processed_at": req.processed_at.isoformat() if req.processed_at else None,
        })
    return result
