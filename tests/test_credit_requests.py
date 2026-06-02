import pytest
import uuid

def test_customer_create_credit_request(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    payload = {
        "account_id": src_id,
        "amount": 1000,
        "customer_note": "Test credit request"
    }

    res = client.post(
        "/customer/credit-requests",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PENDING"
    assert "request_id" in data

def test_customer_list_credit_requests(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    # Create a request first
    client.post(
        "/customer/credit-requests",
        json={
            "account_id": src_id,
            "amount": 500,
            "customer_note": "Salary deposit"
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    res = client.get(
        "/customer/credit-requests",
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["status"] == "PENDING"

def test_admin_list_pending_credit_requests(client, admin_token, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    client.post(
        "/customer/credit-requests",
        json={
            "account_id": src_id,
            "amount": 2000,
            "customer_note": "Business income"
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )

    res = client.get(
        "/admin/credit-requests",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["status"] == "PENDING"
    assert "customer_name" in data[0]

def test_admin_approve_credit_request(client, admin_token, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    # Create request
    req_res = client.post(
        "/customer/credit-requests",
        json={
            "account_id": src_id,
            "amount": 1500,
            "customer_note": "Test approval"
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    request_id = req_res.json()["request_id"]

    # Get balance before
    before_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    before_balance = float(before_res.json()["balance"])

    # Approve
    res = client.post(
        f"/admin/credit-requests/{request_id}/approve",
        json={"admin_note": "Approved for testing"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"

    # Verify balance increased
    after_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    after_balance = float(after_res.json()["balance"])
    assert after_balance == before_balance + 1500

def test_admin_reject_credit_request(client, admin_token, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    req_res = client.post(
        "/customer/credit-requests",
        json={
            "account_id": src_id,
            "amount": 9999,
            "customer_note": "Test rejection"
        },
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    request_id = req_res.json()["request_id"]

    # Get balance before
    before_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    before_balance = float(before_res.json()["balance"])

    # Reject
    res = client.post(
        f"/admin/credit-requests/{request_id}/reject",
        json={"admin_note": "Insufficient documentation"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"

    # Verify balance unchanged
    after_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    after_balance = float(after_res.json()["balance"])
    assert after_balance == before_balance

def test_admin_list_customers(client, admin_token, customer_token):
    res = client.get(
        "/admin/customers",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert "customer_id" in data[0]
    assert "account_count" in data[0]
    assert "total_balance" in data[0]

def test_admin_get_customer_detail(client, admin_token, customer_token):
    profile = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    ).json()
    customer_id = profile["customer_id"]

    res = client.get(
        f"/admin/customers/{customer_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["customer_id"] == customer_id
    assert "accounts" in data
    assert "recent_transactions" in data
