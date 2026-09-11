from datetime import date
from decimal import Decimal


def _setup_invoice(client, headers, amount="10000.00", status="sent"):
    # Create client
    c_res = client.post("/api/clients", headers=headers, json={"name": "Client P", "email": "p@test.com"})
    cid = c_res.get_json()["id"]

    today = date.today().isoformat()
    # Create invoice
    inv_res = client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-PAY-01",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": amount,
        "status": status,
    })
    return inv_res.get_json()["id"]


def test_record_partial_and_full_payment(client, create_user):
    user, headers = create_user(email="payments_test@example.com")
    inv_id = _setup_invoice(client, headers, amount="10000.00", status="sent")
    today = date.today().isoformat()

    # 1. First partial payment: 4,000 -> status should become partially_paid
    res1 = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "4000.00",
        "paid_on": today,
        "method": "upi",
        "reference": "UPI12345",
    })
    assert res1.status_code == 201
    data1 = res1.get_json()
    assert data1["invoice"]["status"] == "partially_paid"
    assert data1["invoice"]["total_paid"] == "4000.00"
    assert data1["invoice"]["balance_due"] == "6000.00"

    # 2. Second payment: 6,000 -> completes invoice, status should become paid
    res2 = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "6000.00",
        "paid_on": today,
        "method": "bank",
        "reference": "NEFT6789",
    })
    assert res2.status_code == 201
    data2 = res2.get_json()
    assert data2["invoice"]["status"] == "paid"
    assert data2["invoice"]["total_paid"] == "10000.00"
    assert data2["invoice"]["balance_due"] == "0.00"


def test_excess_payment_rejected(client, create_user):
    user, headers = create_user(email="excess@example.com")
    inv_id = _setup_invoice(client, headers, amount="5000.00", status="sent")
    today = date.today().isoformat()

    # Try to pay 6,000 against a 5,000 invoice -> 422
    res = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "6000.00",
        "paid_on": today,
        "method": "card",
    })
    assert res.status_code == 422
    assert "exceeds remaining balance" in res.get_json()["error"]


def test_payment_delete_recalculates_status(client, create_user):
    user, headers = create_user(email="recalc@example.com")
    inv_id = _setup_invoice(client, headers, amount="10000.00", status="sent")
    today = date.today().isoformat()

    # Record 4,000 payment
    res_p1 = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "4000.00",
        "paid_on": today,
        "method": "bank",
    })
    p1_id = res_p1.get_json()["payment"]["id"]

    # Record 6,000 payment (now paid in full)
    res_p2 = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "6000.00",
        "paid_on": today,
        "method": "upi",
    })
    p2_id = res_p2.get_json()["payment"]["id"]

    inv_check = client.get(f"/api/invoices/{inv_id}", headers=headers).get_json()
    assert inv_check["status"] == "paid"

    # Delete the 6,000 payment -> status must drop back to partially_paid
    res_del2 = client.delete(f"/api/payments/{p2_id}", headers=headers)
    assert res_del2.status_code == 204

    inv_after_del2 = client.get(f"/api/invoices/{inv_id}", headers=headers).get_json()
    assert inv_after_del2["status"] == "partially_paid"
    assert inv_after_del2["total_paid"] == "4000.00"
    assert inv_after_del2["balance_due"] == "6000.00"

    # Delete the 4,000 payment -> status must revert to sent
    res_del1 = client.delete(f"/api/payments/{p1_id}", headers=headers)
    assert res_del1.status_code == 204

    inv_after_del1 = client.get(f"/api/invoices/{inv_id}", headers=headers).get_json()
    assert inv_after_del1["status"] == "sent"
    assert inv_after_del1["total_paid"] == "0"
    assert inv_after_del1["balance_due"] == "10000.00"


def test_payment_data_isolation(client, create_user):
    user_a, headers_a = create_user(email="pa_a@example.com")
    user_b, headers_b = create_user(email="pa_b@example.com")

    inv_a = _setup_invoice(client, headers_a, amount="8000.00")
    today = date.today().isoformat()

    # User B tries to record payment on User A's invoice -> 404
    res_hack = client.post(f"/api/invoices/{inv_a}/payments", headers=headers_b, json={
        "amount": "1000.00",
        "paid_on": today,
    })
    assert res_hack.status_code == 404

    # User A records payment
    res_p = client.post(f"/api/invoices/{inv_a}/payments", headers=headers_a, json={
        "amount": "1000.00",
        "paid_on": today,
    })
    p_id = res_p.get_json()["payment"]["id"]

    # User B tries to delete User A's payment -> 404
    res_del_hack = client.delete(f"/api/payments/{p_id}", headers=headers_b)
    assert res_del_hack.status_code == 404
