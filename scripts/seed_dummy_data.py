#!/usr/bin/env python3
"""
Seed the Banking Ledger with realistic dummy data for stress testing.
Run: python scripts/seed_dummy_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
import uuid
import time
from decimal import Decimal

# Direct DB access for bootstrapping admin
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.user import User
from app.models.user_role import UserRole
from app.core.security import hash_password

BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "stress_admin"
ADMIN_PASSWORD = "StressAdmin123!"


def bootstrap_admin_if_missing():
    """Directly create admin in DB if not exists (seed scripts can bypass API)."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if existing:
            return

        admin = User(
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            status="ACTIVE"
        )
        db.add(admin)
        db.flush()
        db.add(UserRole(user_id=admin.user_id, role="ADMIN"))
        db.commit()
        print(f"Bootstrapped admin user: {ADMIN_USERNAME}")
    except Exception as e:
        db.rollback()
        print(f"Bootstrap error: {e}")
        raise
    finally:
        db.close()


async def ensure_admin(client: httpx.AsyncClient):
    """Login as admin, bootstrapping via DB if needed."""
    bootstrap_admin_if_missing()

    r = await client.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    )
    if r.status_code == 200:
        return r.json()["access_token"]
    
    raise RuntimeError(f"Admin login failed: {r.status_code} {r.text}")


async def create_customer(client: httpx.AsyncClient, admin_token: str, idx: int):
    """Register a customer and return credentials + account info for stress testing."""
    # Use timestamp + random suffix to guarantee uniqueness across runs
    run_id = f"{int(time.time()) % 10000:04d}"
    unique = f"stress_{run_id}_{idx}_{uuid.uuid4().hex[:4]}"
    password = "Password123!"
    payload = {
        "username": unique,
        "password": password,
        "full_name": f"Stress User {idx}",
        "email": f"{unique}@test.com",
        "phone_number": f"9{run_id}{str(idx).zfill(5)}",  # Unique per run
        "customer_type": "INDIVIDUAL"
    }
    
    r = await client.post(f"{BASE_URL}/auth/register", json=payload)
    if r.status_code != 200:
        print(f"Register failed for {unique}: {r.status_code} {r.text}")
        return None
    
    # Login
    r = await client.post(
        f"{BASE_URL}/auth/login",
        data={"username": unique, "password": password}
    )
    if r.status_code != 200:
        print(f"Login failed for {unique}: {r.status_code} {r.text}")
        return None
    token = r.json()["access_token"]
    
    # Get profile
    r = await client.get(
        f"{BASE_URL}/customer/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    if r.status_code != 200:
        print(f"Profile fetch failed for {unique}: {r.status_code}")
        return None
    customer_id = r.json()["customer_id"]
    
    # Create account
    r = await client.post(
        f"{BASE_URL}/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_id,
            "account_type": "SAVINGS",
            "overdraft_limit": 500
        }
    )
    if r.status_code != 200:
        print(f"Account create failed for {unique}: {r.status_code}")
        return None
    acc = r.json()
    
    # Credit account
    credit_amount = 10_000 + (idx * 1000)
    r = await client.post(
        f"{BASE_URL}/admin/credit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"account_id": acc["account_id"], "amount": credit_amount}
    )
    if r.status_code != 200:
        print(f"Credit failed for {unique}: {r.status_code}")
    
    return {
        "token": token,
        "username": unique,
        "password": password,
        "customer_id": customer_id,
        "account_id": acc["account_id"],
        "account_number": acc["account_number"],
        "balance": credit_amount
    }


async def seed(count: int = 50):
    async with httpx.AsyncClient(timeout=30.0) as client:
        admin_token = await ensure_admin(client)
        print(f"Admin token acquired. Seeding {count} customers...")
        
        tasks = [create_customer(client, admin_token, i) for i in range(count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        customers = [r for r in results if isinstance(r, dict)]
        errors = [r for r in results if isinstance(r, Exception)]
        
        print(f"Seeded {len(customers)} customers. Errors: {len(errors)}")
        
        if errors:
            for e in errors[:3]:
                print(f"  Exception: {e}")
        
        import json
        with open("scripts/stress_customers.json", "w") as f:
            json.dump(customers, f, indent=2)
        print("Saved to scripts/stress_customers.json")


if __name__ == "__main__":
    asyncio.run(seed(50))