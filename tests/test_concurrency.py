import concurrent.futures
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.account_model import Account
from app.models.customer_model import Customer
from app.models.transaction_model import Transaction
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.transaction_service import transfer_money

engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_test_data():
    db = TestingSessionLocal()
    try:
        db.query(AuditLog).delete()
        db.query(Transaction).delete()
        db.query(Account).delete()
        db.query(Customer).delete()
        db.query(User).delete()
        db.commit()

        u1_id, u2_id = uuid4(), uuid4()
        user1 = User(user_id=u1_id, username="test_alice", password_hash="x", status="ACTIVE")
        user2 = User(user_id=u2_id, username="test_bob", password_hash="x", status="ACTIVE")
        db.add_all([user1, user2])
        db.flush()

        c1_id, c2_id = uuid4(), uuid4()
        cust1 = Customer(customer_id=c1_id, user_id=u1_id, full_name="Alice", email="alice@test.com", phone="111", customer_type="INDIVIDUAL")
        cust2 = Customer(customer_id=c2_id, user_id=u2_id, full_name="Bob", email="bob@test.com", phone="222", customer_type="INDIVIDUAL")
        db.add_all([cust1, cust2])
        db.flush()

        a1_id, a2_id = uuid4(), uuid4()
        acc1 = Account(account_id=a1_id, customer_id=c1_id, account_number="ACC_A", account_type="SAVINGS", balance=Decimal("1000.00"), status="ACTIVE")
        acc2 = Account(account_id=a2_id, customer_id=c2_id, account_number="ACC_B", account_type="SAVINGS", balance=Decimal("1000.00"), status="ACTIVE")
        db.add_all([acc1, acc2])
        db.commit()

        return c1_id, a1_id, c2_id, a2_id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def run_concurrent_transfer(customer_id, src_id, dst_id, amount, direction):
    db = TestingSessionLocal()
    try:
        transfer_money(
            db=db,
            customer_id=customer_id,
            source_account_id=src_id,
            destination_account_number="ACC_B" if direction == -1 else "ACC_A",
            amount=Decimal(str(amount)),
            idempotency_key=str(uuid4())
        )
        return direction * amount
    except Exception:
        return 0
    finally:
        db.close()

def test_race_condition():
    c1, a1, c2, a2 = setup_test_data()
    threads = 20
    amount = 10.00

    print(f"Starting {threads} concurrent transfers...")

    net_change_for_a = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for i in range(threads):
            if i % 2 == 0:
                futures.append(executor.submit(run_concurrent_transfer, c1, a1, a2, amount, -1))
            else:
                futures.append(executor.submit(run_concurrent_transfer, c2, a2, a1, amount, 1))

        for f in futures:
            net_change_for_a += f.result()

    db = TestingSessionLocal()
    final_acc1 = db.query(Account).filter(Account.account_id == a1).first()
    final_acc2 = db.query(Account).filter(Account.account_id == a2).first()

    expected_alice = Decimal("1000.00") + Decimal(str(net_change_for_a))
    expected_bob = Decimal("1000.00") - Decimal(str(net_change_for_a))

    print("\n--- RESULTS ---")
    print(f"Net Change Calculated: {net_change_for_a}")
    print(f"Final Balance Alice: {final_acc1.balance} (Expected: {expected_alice})")
    print(f"Final Balance Bob:   {final_acc2.balance} (Expected: {expected_bob})")

    assert final_acc1.balance == expected_alice, f"Alice balance mismatch: {final_acc1.balance} != {expected_alice}"
    assert final_acc2.balance == expected_bob, f"Bob balance mismatch: {final_acc2.balance} != {expected_bob}"
    print("TEST PASSED: Database Consistency Perfect.")

    db.close()

if __name__ == "__main__":
    test_race_condition()
