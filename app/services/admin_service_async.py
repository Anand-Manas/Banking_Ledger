from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from decimal import Decimal

from app.models.user import User
from app.models.user_role import UserRole
from app.models.customer_model import Customer
from app.models.account_model import Account
from app.models.transaction_model import Transaction
from app.core.security_async import hash_password
from app.utils.password_validator import validate_password
from app.schemas.admin_schemas import CreateCustomerRequest, CreateAccountRequest
from app.utils.account_number import generate_account_number

async def create_admin_async(db: AsyncSession, payload):
    result = await db.execute(
        select(User).where(User.username == payload.username)
    )
    existing_admin = result.scalar_one_or_none()

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
    await db.flush()

    db.add(UserRole(user_id=admin.user_id, role="ADMIN"))
    await db.commit()

    return {
        "message": "Admin created successfully",
        "admin_id": str(admin.user_id),
    }

async def promote_customer_to_admin_async(db: AsyncSession, customer_id: str):
    """Promote an existing customer to admin by adding ADMIN role."""
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Check if already has ADMIN role
    existing = await db.execute(
        select(UserRole).where(
            UserRole.user_id == customer.user_id,
            UserRole.role == "ADMIN"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer is already an admin"
        )

    # Add ADMIN role
    db.add(UserRole(user_id=customer.user_id, role="ADMIN"))
    await db.commit()

    return {
        "message": "Customer promoted to admin successfully",
        "user_id": str(customer.user_id),
        "customer_id": str(customer.customer_id),
    }

async def list_admins_async(db: AsyncSession):
    """List all users with ADMIN role."""
    result = await db.execute(
        select(User, Customer).join(
            UserRole, User.user_id == UserRole.user_id
        ).outerjoin(
            Customer, User.user_id == Customer.user_id
        ).where(
            UserRole.role == "ADMIN"
        ).order_by(User.created_at.desc())
    )
    results = result.all()

    output = []
    for user, customer in results:
        output.append({
            "user_id": str(user.user_id),
            "username": user.username,
            "status": user.status,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "roles": ["ADMIN"],  # Could also have CUSTOMER
            "customer_profile": {
                "customer_id": str(customer.customer_id) if customer else None,
                "full_name": customer.full_name if customer else None,
                "email": customer.email if customer else None,
                "phone": customer.phone if customer else None,
            } if customer else None,
        })
    return output

async def create_customer_async(db: AsyncSession, payload: CreateCustomerRequest):
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    result = await db.execute(
        select(Customer).where(
            (Customer.email == payload.email) | (Customer.phone == payload.phone)
        )
    )
    if result.scalar_one_or_none():
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
        await db.flush()

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
        await db.commit()

        return {
            "customer_id": str(customer.customer_id)
        }
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Data integrity error (duplicate key)")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

async def create_account_async(db: AsyncSession, payload: CreateAccountRequest):
    result = await db.execute(
        select(Customer).where(Customer.customer_id == payload.customer_id)
    )
    customer = result.scalar_one_or_none()
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
    await db.commit()
    await db.refresh(account)

    return {
        "account_id": str(account.account_id),
        "account_number": account.account_number,
    }

async def list_customers_async(db: AsyncSession):
    result = await db.execute(
        select(Customer, func.count(Account.account_id).label("account_count"),
               func.coalesce(func.sum(Account.balance), 0).label("total_balance"))
        .outerjoin(Account, Customer.customer_id == Account.customer_id)
        .group_by(Customer)
    )
    results = result.all()

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

async def get_customer_details_async(db: AsyncSession, customer_id: str):
    result = await db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    acc_result = await db.execute(
        select(Account).where(Account.customer_id == customer_id)
    )
    accounts = acc_result.scalars().all()
    account_ids = [a.account_id for a in accounts]

    recent_transactions = []
    if account_ids:
        txn_result = await db.execute(
            select(Transaction)
            .where(
                or_(
                    Transaction.source_account_id.in_(account_ids),
                    Transaction.destination_account_id.in_(account_ids)
                )
            )
            .order_by(Transaction.created_at.desc())
            .limit(10)
        )
        recent_transactions = txn_result.scalars().all()

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