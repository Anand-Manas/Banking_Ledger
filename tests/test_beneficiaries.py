import pytest
import uuid

FAKE_BENEFICIARY_NUMBER = "999999999999"  # Does not belong to test customer


def test_add_beneficiary(client, customer_token):
    res = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": FAKE_BENEFICIARY_NUMBER, "bank_name": "Test Bank"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["beneficiary_account_number"] == FAKE_BENEFICIARY_NUMBER
    assert data["bank_name"] == "Test Bank"
    assert data["status"] == "ACTIVE"


def test_list_beneficiaries_active_only(client, customer_token):
    # Add beneficiary
    add_res = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": FAKE_BENEFICIARY_NUMBER, "bank_name": "Test Bank"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert add_res.status_code == 200

    # List should show it
    list_res = client.get(
        "/beneficiaries/",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert len(data) >= 1
    assert any(b["account_number"] == FAKE_BENEFICIARY_NUMBER for b in data)


def test_self_beneficiary_blocked(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    # Get source account number (belongs to same customer)
    src_res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert src_res.status_code == 200
    src_number = src_res.json()["account_number"]

    res = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": src_number, "bank_name": "Self"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 400
    assert "own" in res.json()["detail"].lower()


def test_duplicate_beneficiary_blocked(client, customer_token):
    # Add first time
    r1 = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": FAKE_BENEFICIARY_NUMBER, "bank_name": "Test Bank"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert r1.status_code == 200

    # Try duplicate
    r2 = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": FAKE_BENEFICIARY_NUMBER, "bank_name": "Test Bank 2"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


def test_delete_beneficiary_soft_delete(client, customer_token):
    add_res = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": FAKE_BENEFICIARY_NUMBER, "bank_name": "Test Bank"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert add_res.status_code == 200
    ben_id = add_res.json()["beneficiary_id"]

    # Soft delete
    del_res = client.delete(
        f"/beneficiaries/{ben_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "INACTIVE"

    # List should NOT show it
    list_res = client.get(
        "/beneficiaries/",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert list_res.status_code == 200
    for b in list_res.json():
        assert b["beneficiary_id"] != ben_id

    # Re-adding should succeed (duplicate check only blocks ACTIVE)
    r3 = client.post(
        "/beneficiaries/",
        params={"beneficiary_account_number": FAKE_BENEFICIARY_NUMBER, "bank_name": "Test Bank"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert r3.status_code == 200