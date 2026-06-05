import pytest
import uuid


def test_account_statement_shows_transfers(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    # Execute a transfer
    transfer_res = client.post(
        "/transactions/transfer",
        json={
            "source_account_id": src_id,
            "destination_account_number": dst_number,
            "amount": 250,
            "idempotency_key": f"stmt-{uuid.uuid4()}",
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert transfer_res.status_code == 200

    # Check statement
    res = client.get(
        f"/transactions/statement/{src_id}?limit=5",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == src_id
    assert "current_balance" in data
    assert len(data["transactions"]) >= 1
    txn = data["transactions"][0]
    assert txn["type"] == "TRANSFER"
    assert txn["amount"] == "250.00"  # Numeric(15,2) preserves 2 decimals
    assert txn["status"] == "SUCCESS"


def test_statement_limit_parameter(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    # Execute 3 transfers
    for i in range(3):
        r = client.post(
            "/transactions/transfer",
            json={
                "source_account_id": src_id,
                "destination_account_number": dst_number,
                "amount": 10,
                "idempotency_key": f"stmt-limit-{uuid.uuid4()}-{i}",
            },
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert r.status_code == 200

    res = client.get(
        f"/transactions/statement/{src_id}?limit=2",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    assert len(res.json()["transactions"]) == 2