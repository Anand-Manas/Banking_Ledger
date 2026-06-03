from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.api.deps import require_customer
from app.models.beneficiary_model import Beneficiary
from app.models.customer_model import Customer
from app.models.account_model import Account

router = APIRouter()

@router.post("/")
def add_beneficiary(
    beneficiary_account_number: str,
    bank_name: str,
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # BLOCK: Cannot add your own account as beneficiary
    own_account = db.query(Account).filter(
        Account.account_number == beneficiary_account_number,
        Account.customer_id == customer.customer_id
    ).first()

    if own_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add your own account as a beneficiary"
        )

    # BLOCK: Duplicate beneficiary
    existing = db.query(Beneficiary).filter(
        Beneficiary.customer_id == customer.customer_id,
        Beneficiary.beneficiary_account_number == beneficiary_account_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Beneficiary already exists"
        )

    beneficiary = Beneficiary(
        customer_id=customer.customer_id,
        beneficiary_account_number=beneficiary_account_number,
        bank_name=bank_name,
    )
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)

    return {
        "beneficiary_id": str(beneficiary.beneficiary_id),
        "beneficiary_account_number": beneficiary.beneficiary_account_number,
        "bank_name": beneficiary.bank_name,
        "status": beneficiary.status,
    }

@router.get("/")
def list_beneficiaries(
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    beneficiaries = db.query(Beneficiary).filter(
        Beneficiary.customer_id == customer.customer_id,
        Beneficiary.status == "ACTIVE"
    ).all()

    return [
        {
            "beneficiary_id": str(b.beneficiary_id),
            "account_number": b.beneficiary_account_number,
            "bank_name": b.bank_name,
            "status": b.status,
        }
        for b in beneficiaries
    ]

@router.delete("/{beneficiary_id}")
def remove_beneficiary(
    beneficiary_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_customer)
):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Ownership check: must belong to this customer
    beneficiary = db.query(Beneficiary).filter(
        Beneficiary.beneficiary_id == beneficiary_id,
        Beneficiary.customer_id == customer.customer_id
    ).first()

    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beneficiary not found"
        )

    # Soft delete: mark INACTIVE instead of hard delete
    beneficiary.status = "INACTIVE"
    db.commit()

    return {
        "beneficiary_id": str(beneficiary.beneficiary_id),
        "status": "INACTIVE",
        "message": "Beneficiary removed successfully"
    }