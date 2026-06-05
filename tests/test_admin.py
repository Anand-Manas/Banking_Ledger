import pytest
import uuid


def test_create_admin(client, admin_token):
    unique = uuid.uuid4().hex[:6]
    res = client.post(
        "/admin/admins",
        json={
            "username": f"new_admin_{unique}",
            "password": "AdminPass123!",
            "email": f"admin_{unique}@test.com"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "admin_id" in data


def test_list_admins(client, admin_token):
    res = client.get(
        "/admin/admins",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    # Fixture creates test_admin, so at least one admin must exist
    assert any("ADMIN" in a.get("roles", []) for a in data)


def test_promote_customer_to_admin(client, admin_token, customer_token):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()
    customer_id = profile["customer_id"]

    # Promote
    res = client.post(
        f"/admin/customers/{customer_id}/promote",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert "promoted" in res.json()["message"].lower()

    # Duplicate promotion should fail
    res2 = client.post(
        f"/admin/customers/{customer_id}/promote",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res2.status_code == 409
    assert "already" in res2.json()["detail"].lower()


def test_direct_credit_frozen_account(client, admin_token, customer_token, db_session):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()

    acc = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()
    account_id = acc["account_id"]

    # Freeze via DB
    from app.models.account_model import Account
    db_session.query(Account).filter(Account.account_id == account_id).update({"status": "FROZEN"})
    db_session.commit()

    res = client.post(
        "/admin/credit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"account_id": account_id, "amount": 1000}
    )
    assert res.status_code == 400
    assert "frozen" in res.json()["detail"].lower()


def test_direct_credit_closed_account(client, admin_token, customer_token, db_session):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()

    acc = client.post(
        "/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": profile["customer_id"],
            "account_type": "SAVINGS",
            "overdraft_limit": 0
        }
    ).json()
    account_id = acc["account_id"]

    # Close via DB
    from app.models.account_model import Account
    db_session.query(Account).filter(Account.account_id == account_id).update({"status": "CLOSED"})
    db_session.commit()

    res = client.post(
        "/admin/credit",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"account_id": account_id, "amount": 1000}
    )
    assert res.status_code == 400
    assert "closed" in res.json()["detail"].lower()