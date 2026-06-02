import pytest
import uuid

def test_atomic_transfer(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    payload = {
        "source_account_id": src_id,
        "destination_account_number": dst_number,
        "amount": 100.00,
        "idempotency_key": f"atomic-{uuid.uuid4()}",
    }

    res = client.post(
        "/transactions/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert "transaction_id" in data
    assert data["status"] == "SUCCESS"

def test_idempotency(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts
    idem_key = f"idem-{uuid.uuid4()}"

    before_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert before_res.status_code == 200
    before_balance = float(before_res.json()["balance"])

    payload = {
        "source_account_id": src_id,
        "destination_account_number": dst_number,
        "amount": 500,
        "idempotency_key": idem_key,
    }

    res1 = client.post(
        "/transactions/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res1.status_code == 200

    res2 = client.post(
        "/transactions/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res2.status_code == 200

    after_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert after_res.status_code == 200
    after_balance = float(after_res.json()["balance"])

    assert before_balance - after_balance == 500.0

def test_self_transfer_rejected(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    # Get source account number
    src_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    src_number = src_res.json()["account_number"]

    payload = {
        "source_account_id": src_id,
        "destination_account_number": src_number,
        "amount": 100,
        "idempotency_key": f"self-{uuid.uuid4()}",
    }

    res = client.post(
        "/transactions/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert res.status_code == 400
    assert "same" in res.json()["detail"].lower()

def test_negative_amount_rejected(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    payload = {
        "source_account_id": src_id,
        "destination_account_number": dst_number,
        "amount": -100,
        "idempotency_key": f"neg-{uuid.uuid4()}",
    }

    res = client.post(
        "/transactions/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert res.status_code == 422

def test_destination_account_not_found(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    payload = {
        "source_account_id": src_id,
        "destination_account_number": "999999999999",
        "amount": 100,
        "idempotency_key": f"notfound-{uuid.uuid4()}",
    }

    res = client.post(
        "/transactions/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
