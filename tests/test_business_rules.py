import pytest
import uuid
from decimal import Decimal


def test_overdraft_limit_enforced(client, customer_token, overdraft_account_id, seeded_accounts):
    """overdraft_account_id has balance=0, overdraft_limit=100."""
    src_id, dst_id, dst_number = seeded_accounts

    # Try to transfer 200 (overdraft allows only 100)
    res = client.post(
        "/transactions/transfer",
        json={
            "source_account_id": overdraft_account_id,
            "destination_account_number": dst_number,
            "amount": 200,
            "idempotency_key": f"od-{uuid.uuid4()}",
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 400
    assert "overdraft" in res.json()["detail"].lower()


def test_min_balance_enforced(client, customer_token, admin_token, db_session):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()

    # Create source account and credit it
    src = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()

    client.post(
        "/admin/credit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"account_id": src["account_id"], "amount": 5000}
    )

    # Set min_balance=1000 via DB (no API field for this)
    from app.models.account_model import Account
    db_session.query(Account).filter(Account.account_id == src["account_id"]).update({"min_balance": Decimal("1000")})
    db_session.commit()

    # Create destination
    dst = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()

    # Try to transfer 4500 (balance=5000, min_balance=1000, max allowed=4000)
    res = client.post(
        "/transactions/transfer",
        json={
            "source_account_id": src["account_id"],
            "destination_account_number": dst["account_number"],
            "amount": 4500,
            "idempotency_key": f"minbal-{uuid.uuid4()}",
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 400
    assert "minimum balance" in res.json()["detail"].lower()


def test_transfer_source_frozen_returns_403(client, customer_token, seeded_accounts, db_session):
    """
    The transactions router filters source_account.status == "ACTIVE".
    So a FROZEN source account fails the ownership check with 403.
    """
    src_id, dst_id, dst_number = seeded_accounts

    from app.models.account_model import Account
    db_session.query(Account).filter(Account.account_id == src_id).update({"status": "FROZEN"})
    db_session.commit()

    res = client.post(
        "/transactions/transfer",
        json={
            "source_account_id": src_id,
            "destination_account_number": dst_number,
            "amount": 100,
            "idempotency_key": f"frozensrc-{uuid.uuid4()}",
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 403
    assert "not found or does not belong to you" in res.json()["detail"].lower()

    # Restore for other tests (function-scoped fixtures create new accounts,
    # but let's be safe)
    db_session.query(Account).filter(Account.account_id == src_id).update({"status": "ACTIVE"})
    db_session.commit()


def test_transfer_destination_frozen_returns_404(client, customer_token, admin_token, db_session):
    """
    The service queries destination by account_number with status == "ACTIVE".
    So a FROZEN destination returns 404 "not found".
    """
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()

    # Create a destination account
    dst = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()

    # Freeze it
    from app.models.account_model import Account
    db_session.query(Account).filter(Account.account_id == dst["account_id"]).update({"status": "FROZEN"})
    db_session.commit()

    # Need a source account with balance
    src = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()
    client.post(
        "/admin/credit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"account_id": src["account_id"], "amount": 1000}
    )

    res = client.post(
        "/transactions/transfer",
        json={
            "source_account_id": src["account_id"],
            "destination_account_number": dst["account_number"],
            "amount": 100,
            "idempotency_key": f"frozendst-{uuid.uuid4()}",
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()