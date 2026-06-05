import pytest
import os
import sys
import uuid
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import app
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User
from app.models.user_role import UserRole
from app.models.customer_model import Customer
from app.models.account_model import Account
from app.models.audit_log import AuditLog
from app.models.credit_request import CreditRequest  # ← ADD
from app.core.security import hash_password

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def admin_token(client):
    db = SessionLocal()
    try:
        # FIX: Delete credit_requests where this admin was processor
        db.query(CreditRequest).filter(CreditRequest.processed_by.in_(
            db.query(User.user_id).filter(User.username == "test_admin")
        )).delete(synchronize_session=False)

        # FIX: Delete audit_logs FIRST (FK to users)
        db.query(AuditLog).filter(AuditLog.user_id.in_(
            db.query(User.user_id).filter(User.username == "test_admin")
        )).delete(synchronize_session=False)
        
        db.query(UserRole).filter(UserRole.user_id.in_(
            db.query(User.user_id).filter(User.username == "test_admin")
        )).delete(synchronize_session=False)
        db.query(User).filter(User.username == "test_admin").delete()
        db.commit()

        admin = User(
            username="test_admin",
            password_hash=hash_password("test_admin_pass_123"),
            status="ACTIVE"
        )
        db.add(admin)
        db.flush()

        db.add(UserRole(user_id=admin.user_id, role="ADMIN"))
        db.commit()
    finally:
        db.close()

    res = client.post(
        "/auth/login",
        data={"username": "test_admin", "password": "test_admin_pass_123"}
    )
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture(scope="function")
def customer_token(client):
    unique_user = f"user_{uuid.uuid4().hex[:6]}"
    unique_email = f"{unique_user}@test.com"
    unique_phone = str(uuid.uuid4().int)[:10]

    client.post(
        "/auth/register",
        json={
            "username": unique_user,
            "password": "Password123!",
            "full_name": "Test User",
            "email": unique_email,
            "phone_number": unique_phone,
            "customer_type": "INDIVIDUAL"
        }
    )

    res = client.post(
        "/auth/login",
        data={"username": unique_user, "password": "Password123!"}
    )
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture(scope="function")
def seeded_accounts(client, admin_token, customer_token):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()

    customer_id = profile["customer_id"]

    src = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_id,
            "account_type": "SAVINGS",
            "overdraft_limit": 5000
        }
    ).json()

    dst = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_id,
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()

    client.post(
        "/admin/credit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "account_id": src["account_id"],
            "amount": 50000
        }
    )

    return src["account_id"], dst["account_id"], dst["account_number"]

@pytest.fixture(scope="function")
def overdraft_account_id(client, admin_token, customer_token):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()

    res = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 100
        }
    ).json()

    return res["account_id"]