from datetime import date, timedelta
from decimal import Decimal


def _create_test_client(client, headers, name="Acme", email="acme@test.com"):
    res = client.post("/api/clients", headers=headers, json={"name": name, "email": email})
    return res.get_json()["id"]


def test_invoice_crud(client, create_user):
    user, headers = create_user(email="inv_crud@example.com")
    cid = _create_test_client(client, headers)

    today = date.today()
    # Create invoice
    res = client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-001",
        "client_id": cid,
        "issue_date": today.isoformat(),
        "due_date": (today + timedelta(days=15)).isoformat(),
        "amount": "15000.00",
        "currency": "INR",
        "description": "Consulting services",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["invoice_number"] == "INV-001"
    assert data["amount"] == "15000.00"
    assert data["status"] == "draft"
    inv_id = data["id"]

    # Get invoice detail
    res_get = client.get(f"/api/invoices/{inv_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.get_json()["description"] == "Consulting services"

    # Update invoice (change status to sent)
    res_update = client.put(f"/api/invoices/{inv_id}", headers=headers, json={
        "status": "sent",
        "description": "Updated consulting scope",
    })
    assert res_update.status_code == 200
    assert res_update.get_json()["status"] == "sent"

    # Soft delete invoice
    res_del = client.delete(f"/api/invoices/{inv_id}", headers=headers)
    assert res_del.status_code == 204

    # Subsequent GET returns 404
    res_after = client.get(f"/api/invoices/{inv_id}", headers=headers)
    assert res_after.status_code == 404


def test_invoice_duplicate_number_rejected(client, create_user):
    user, headers = create_user(email="dup_inv@example.com")
    cid = _create_test_client(client, headers)
    today = date.today().isoformat()

    payload = {
        "invoice_number": "INV-DUP-1",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": "5000.00",
    }
    res1 = client.post("/api/invoices", headers=headers, json=payload)
    assert res1.status_code == 201

    # Same user, same invoice number -> 409 Conflict
    res2 = client.post("/api/invoices", headers=headers, json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.get_json()["error"]


def test_same_invoice_number_different_users_allowed(client, create_user):
    user_a, headers_a = create_user(email="user_a_dup@example.com")
    user_b, headers_b = create_user(email="user_b_dup@example.com")

    cid_a = _create_test_client(client, headers_a, email="ca@test.com")
    cid_b = _create_test_client(client, headers_b, email="cb@test.com")
    today = date.today().isoformat()

    # User A creates INV-SHARED-1
    res_a = client.post("/api/invoices", headers=headers_a, json={
        "invoice_number": "INV-SHARED-1",
        "client_id": cid_a,
        "issue_date": today,
        "due_date": today,
        "amount": "1000.00",
    })
    assert res_a.status_code == 201

    # User B creates INV-SHARED-1 -> allowed!
    res_b = client.post("/api/invoices", headers=headers_b, json={
        "invoice_number": "INV-SHARED-1",
        "client_id": cid_b,
        "issue_date": today,
        "due_date": today,
        "amount": "2000.00",
    })
    assert res_b.status_code == 201


def test_invoice_date_validation(client, create_user):
    user, headers = create_user(email="dates@example.com")
    cid = _create_test_client(client, headers)

    # due_date before issue_date -> 422
    res = client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-DATES",
        "client_id": cid,
        "issue_date": "2026-09-10",
        "due_date": "2026-09-01",
        "amount": "1000.00",
    })
    assert res.status_code == 422
    assert "due_date must be on or after issue_date" in res.get_json()["error"]


def test_invoice_csv_export(client, create_user):
    user, headers = create_user(email="export@example.com")
    cid = _create_test_client(client, headers, name="Export Client", email="export@client.com")
    today = date.today().isoformat()

    client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-EXP-1",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": "12500.00",
        "currency": "INR",
        "description": "Export test",
    })

    res = client.get("/api/invoices/export", headers=headers)
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert "attachment; filename=invoices.csv" in res.headers["Content-Disposition"]

    content = res.data.decode("utf-8")
    assert "Invoice Number,Client Name,Client Email" in content
    assert "INV-EXP-1,Export Client,export@client.com" in content
    assert "12500.00" in content
