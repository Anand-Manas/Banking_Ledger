from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.user_role import UserRole
from app.models.customer_model import Customer
from app.models.account_model import Account
from app.models.transaction_model import Transaction
from app.core.security import hash_password
from app.utils.password_validator import validate_password
from app.schemas.admin_schemas import CreateCustomerRequest, CreateAccountRequest
from app.utils.account_number import generate_account_number


def create_admin(db, payload):
    existing_admin = (
        db.query(User)
        .filter(User.username == payload.username)
        .first()
    )

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin with this username already exists",
        )

    validate_password(payload.password)

    admin = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        status="ACTIVE",
    )

    db.add(admin)
    db.flush()

    db.add(UserRole(user_id=admin.user_id, role="ADMIN"))
    db.commit()

    return {
        "message": "Admin created successfully",
        "admin_id": str(admin.user_id),
    }

def create_customer(db: Session, payload: CreateCustomerRequest):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    if db.query(Customer).filter(
        (Customer.email == payload.email) | (Customer.phone == payload.phone)
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or Phone already registered"
        )

    try:
        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            status="ACTIVE",
        )
        db.add(user)
        db.flush() 

        db.add(UserRole(user_id=user.user_id, role="CUSTOMER"))

        customer = Customer(
            user_id=user.user_id,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            address=payload.address,
            customer_type=payload.customer_type,
        )
        db.add(customer)
        db.commit()

        return {
            "customer_id": str(customer.customer_id)
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Data integrity error (duplicate key)")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def create_account(db: Session, payload: CreateAccountRequest):
    customer = (
        db.query(Customer)
        .filter(Customer.customer_id == payload.customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    account = Account(
        customer_id=payload.customer_id,
        account_number=generate_account_number(),
        account_type=payload.account_type,
        overdraft_limit=payload.overdraft_limit,
        balance=0,
        status="ACTIVE",
    )
    db.add(account)
    db.commit()

    return {
        "account_id": str(account.account_id),
        "account_number": account.account_number,
    }


def list_customers(db: Session):
    results = db.query(
        Customer,
        func.count(Account.account_id).label("account_count"),
        func.coalesce(func.sum(Account.balance), 0).label("total_balance")
    ).outerjoin(
        Account, Customer.customer_id == Account.customer_id
    ).group_by(Customer).all()

    output = []
    for customer, account_count, total_balance in results:
        user_status = "ACTIVE"
        if customer.user:
            user_status = customer.user.status

        output.append({
            "customer_id": str(customer.customer_id),
            "full_name": customer.full_name,
            "email": customer.email,
            "phone": customer.phone,
            "customer_type": customer.customer_type,
            "account_count": account_count,
            "total_balance": str(total_balance),
            "status": user_status,
        })
    return output


def get_customer_details(db: Session, customer_id: str):
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
    account_ids = [a.account_id for a in accounts]

    recent_transactions = []
    if account_ids:
        recent_transactions = db.query(Transaction).filter(
            or_(
                Transaction.source_account_id.in_(account_ids),
                Transaction.destination_account_id.in_(account_ids)
            )
        ).order_by(Transaction.created_at.desc()).limit(10).all()

    return {
        "customer_id": str(customer.customer_id),
        "full_name": customer.full_name,
        "email": customer.email,
        "phone": customer.phone,
        "customer_type": customer.customer_type,
        "address": customer.address,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "accounts": [
            {
                "account_id": str(a.account_id),
                "account_number": a.account_number,
                "account_type": a.account_type,
                "balance": str(a.balance),
                "status": a.status,
                "overdraft_limit": str(a.overdraft_limit),
            }
            for a in accounts
        ],
        "recent_transactions": [
            {
                "transaction_id": str(t.transaction_id),
                "type": t.transaction_type,
                "amount": str(t.amount),
                "status": t.status,
                "timestamp": t.created_at.isoformat() if t.created_at else None,
            }
            for t in recent_transactions
        ]
    }
