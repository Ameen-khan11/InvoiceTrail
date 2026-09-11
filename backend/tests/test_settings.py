def test_settings_endpoints(client, create_user):
    user, headers = create_user(email="settings@example.com", name="Settings User", is_pro=False)

    # 1. Get settings
    res = client.get("/api/settings", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["email"] == "settings@example.com"
    assert data["usage"]["is_pro"] is False
    assert data["usage"]["clients"]["limit"] == 5
    assert data["usage"]["invoices"]["limit"] == 20

    # 2. Update settings (profile and reminder toggle)
    res_put = client.put("/api/settings", headers=headers, json={
        "name": "Updated Name",
        "business_name": "Updated Agency",
        "email_reminders_enabled": False,
    })
    assert res_put.status_code == 200
    updated_user = res_put.get_json()["user"]
    assert updated_user["name"] == "Updated Name"
    assert updated_user["business_name"] == "Updated Agency"
    assert updated_user["email_reminders_enabled"] is False

    # 3. Blank name validation
    res_bad = client.put("/api/settings", headers=headers, json={"name": "   "})
    assert res_bad.status_code == 422
    assert "Name cannot be blank" in res_bad.get_json()["error"]
