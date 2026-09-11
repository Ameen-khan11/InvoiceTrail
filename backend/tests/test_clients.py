from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models import Invoice


def test_client_crud(client, create_user):
    user, headers = create_user(email="client_crud@example.com")

    # Create client
    res = client.post("/api/clients", headers=headers, json={
        "name": "Acme Global",
        "email": "acme@example.com",
        "company": "Acme Inc",
        "phone": "1234567890",
        "notes": "VIP client",
    })
    assert res.status_code == 201
    c_data = res.get_json()
    client_id = c_data["id"]
    assert c_data["name"] == "Acme Global"

    # List clients
    res_list = client.get("/api/clients", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.get_json()["clients"]) == 1

    # Get client detail
    res_get = client.get(f"/api/clients/{client_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.get_json()["email"] == "acme@example.com"

    # Update client
    res_update = client.put(f"/api/clients/{client_id}", headers=headers, json={
        "name": "Acme Enterprises",
        "phone": "9876543210",
    })
    assert res_update.status_code == 200
    assert res_update.get_json()["name"] == "Acme Enterprises"
    assert res_update.get_json()["phone"] == "9876543210"

    # Delete client
    res_del = client.delete(f"/api/clients/{client_id}", headers=headers)
    assert res_del.status_code == 204

    # Verify deleted
    res_after = client.get(f"/api/clients/{client_id}", headers=headers)
    assert res_after.status_code == 404


def test_client_data_isolation(client, create_user):
    user_a, headers_a = create_user(email="user_a@example.com")
    user_b, headers_b = create_user(email="user_b@example.com")

    # User A creates a client
    res_a = client.post("/api/clients", headers=headers_a, json={
        "name": "User A Private Client",
        "email": "private@example.com",
    })
    client_id = res_a.get_json()["id"]

    # User B tries to view User A's client -> MUST return 404 (not 403, not 200)
    res_b_get = client.get(f"/api/clients/{client_id}", headers=headers_b)
    assert res_b_get.status_code == 404

    # User B tries to update User A's client -> 404
    res_b_put = client.put(f"/api/clients/{client_id}", headers=headers_b, json={"name": "Hacked"})
    assert res_b_put.status_code == 404

    # User B tries to delete User A's client -> 404
    res_b_del = client.delete(f"/api/clients/{client_id}", headers=headers_b)
    assert res_b_del.status_code == 404


def test_free_plan_client_limit(client, create_user):
    user, headers = create_user(email="free_plan@example.com", is_pro=False)

    # Free plan limit is 5 clients
    for i in range(5):
        res = client.post("/api/clients", headers=headers, json={
            "name": f"Client {i}",
            "email": f"client{i}@example.com",
        })
        assert res.status_code == 201

    # 6th client must be rejected with 403
    res_sixth = client.post("/api/clients", headers=headers, json={
        "name": "Client 6",
        "email": "client6@example.com",
    })
    assert res_sixth.status_code == 403
    assert "Free plan is limited to 5 clients" in res_sixth.get_json()["error"]


def test_delete_client_with_invoices_blocked(client, create_user):
    user, headers = create_user(email="client_blocked@example.com")

    # Create client
    res_c = client.post("/api/clients", headers=headers, json={
        "name": "Client With Invoices",
        "email": "invoiced@example.com",
    })
    cid = res_c.get_json()["id"]

    # Attach an invoice
    inv = Invoice(
        user_id=user.id,
        client_id=cid,
        invoice_number="INV-DEL-01",
        issue_date=date(2026, 8, 1),
        due_date=date(2026, 8, 30),
        amount=Decimal("5000.00"),
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # Delete must be blocked with 409
    res_del = client.delete(f"/api/clients/{cid}", headers=headers)
    assert res_del.status_code == 409
    assert "Delete or reassign them first" in res_del.get_json()["error"]
