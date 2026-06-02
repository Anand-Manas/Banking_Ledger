from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_customer, get_current_user
from app.models.beneficiary_model import Beneficiary
from app.models.customer_model import Customer

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

    beneficiary = Beneficiary(
        customer_id=customer.customer_id,
        beneficiary_account_number=beneficiary_account_number,
        bank_name=bank_name,
    )
    db.add(beneficiary)
    db.commit()
    return {"beneficiary_id": str(beneficiary.beneficiary_id)}

@router.get("/")
def list_beneficiaries(db: Session = Depends(get_db), user=Depends(require_customer)):
    customer = db.query(Customer).filter(Customer.user_id == user.user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    beneficiaries = db.query(Beneficiary).filter(
        Beneficiary.customer_id == customer.customer_id
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
