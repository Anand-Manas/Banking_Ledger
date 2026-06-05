def test_customer_profile(client, customer_token):
    res = client.get(
        "/customer/profile",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "customer_id" in data
    assert "full_name" in data
    assert "email" in data
    assert "phone" in data


def test_customer_list_accounts(client, customer_token, seeded_accounts):
    res = client.get(
        "/customer/accounts",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2  # seeded_accounts creates 2 accounts
    assert "account_number" in data[0]
    assert "balance" in data[0]


def test_customer_get_single_account(client, customer_token, seeded_accounts):
    src_id, dst_id, dst_number = seeded_accounts

    res = client.get(
        f"/customer/accounts/{src_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == src_id
    assert "account_number" in data
    assert "balance" in data