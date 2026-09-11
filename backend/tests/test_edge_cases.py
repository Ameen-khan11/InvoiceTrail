"""InvoiceTrail — Explicit Test Suite for all 6 Specification Edge Cases (Spec Section 8)."""

from datetime import date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Client, Invoice, Payment, ReminderLog
from cron_job import run_daily_reminders


def test_edge_case_1_duplicate_invoice_number(client, create_user):
    """Edge Case 1: Two invoices, same number, same user -> rejected with 409, not a database crash."""
    user, headers = create_user(email="ec1@example.com")
    c_res = client.post("/api/clients", headers=headers, json={"name": "Client 1", "email": "c1@test.com"})
    cid = c_res.get_json()["id"]

    today = date.today().isoformat()
    payload = {
        "invoice_number": "INV-CONFLICT-01",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": "1000.00",
    }
    res1 = client.post("/api/invoices", headers=headers, json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/invoices", headers=headers, json=payload)
    assert res2.status_code == 409
    assert res2.get_json()["error"] == "This invoice number already exists"
    assert res2.get_json()["field"] == "invoice_number"


def test_edge_case_2_excess_payment_rejected(client, create_user):
    """Edge Case 2: Payment of 5,000 recorded against an invoice with a 3,000 balance -> rejected cleanly."""
    user, headers = create_user(email="ec2@example.com")
    c_res = client.post("/api/clients", headers=headers, json={"name": "Client 2", "email": "c2@test.com"})
    cid = c_res.get_json()["id"]

    today = date.today().isoformat()
    # Create invoice of 3,000
    inv_res = client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-3000",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": "3000.00",
        "status": "sent",
    })
    inv_id = inv_res.get_json()["id"]

    # Try to pay 5,000 against a 3,000 balance
    res_excess = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "5000.00",
        "paid_on": today,
        "method": "upi",
    })
    assert res_excess.status_code == 422
    assert "exceeds remaining balance of 3000.00" in res_excess.get_json()["error"]


def test_edge_case_3_delete_payment_on_paid_invoice(client, create_user):
    """Edge Case 3: Deleting a payment on a fully paid invoice -> status drops back to partially_paid correctly."""
    user, headers = create_user(email="ec3@example.com")
    c_res = client.post("/api/clients", headers=headers, json={"name": "Client 3", "email": "c3@test.com"})
    cid = c_res.get_json()["id"]

    today = date.today().isoformat()
    # Create invoice of 10,000
    inv_res = client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-10000",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": "10000.00",
        "status": "sent",
    })
    inv_id = inv_res.get_json()["id"]

    # 1. Partial payment of 4,000
    client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "4000.00",
        "paid_on": today,
        "method": "bank",
    })

    # 2. Final payment of 6,000 -> completes to 'paid'
    res_p2 = client.post(f"/api/invoices/{inv_id}/payments", headers=headers, json={
        "amount": "6000.00",
        "paid_on": today,
        "method": "upi",
    })
    p2_id = res_p2.get_json()["payment"]["id"]

    inv_after_full = client.get(f"/api/invoices/{inv_id}", headers=headers).get_json()
    assert inv_after_full["status"] == "paid"

    # Delete the 6,000 payment
    res_del = client.delete(f"/api/payments/{p2_id}", headers=headers)
    assert res_del.status_code == 204

    # Status MUST drop back to partially_paid (with balance_due of 6,000)
    inv_recalculated = client.get(f"/api/invoices/{inv_id}", headers=headers).get_json()
    assert inv_recalculated["status"] == "partially_paid"
    assert inv_recalculated["total_paid"] == "4000.00"
    assert inv_recalculated["balance_due"] == "6000.00"


def test_edge_case_4_daily_job_double_run_idempotency(app, create_user):
    """Edge Case 4: The daily job is run twice by accident -> the second run sends zero emails."""
    user, _ = create_user(email="ec4@example.com", name="EC4 User")
    user.email_reminders_enabled = True

    c = Client(user_id=user.id, name="Overdue Client", email="c4@test.com")
    db.session.add(c)
    db.session.commit()

    today = date.today()
    inv = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="INV-EC4-OVERDUE",
        issue_date=today - timedelta(days=20),
        due_date=today - timedelta(days=5),
        amount=Decimal("15000.00"),
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # First run sends 1 email
    stats1 = run_daily_reminders(app=app)
    assert stats1["emails_sent"] == 1

    # Second run on the exact same date sends 0 emails
    stats2 = run_daily_reminders(app=app)
    assert stats2["emails_sent"] == 0
    assert stats2["skipped_already_sent"] == 1


def test_edge_case_5_invoice_due_today_not_overdue(client, create_user):
    """Edge Case 5: Invoice due today at 23:59 -> rule is due_date < today, so it is NOT overdue today."""
    user, headers = create_user(email="ec5@example.com")
    c_res = client.post("/api/clients", headers=headers, json={"name": "Client 5", "email": "c5@test.com"})
    cid = c_res.get_json()["id"]

    today = date.today()

    # Invoice due today
    res = client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-DUE-TODAY",
        "client_id": cid,
        "issue_date": today.isoformat(),
        "due_date": today.isoformat(),
        "amount": "5000.00",
        "status": "sent",
    })
    inv_data = res.get_json()

    # Derived state is_overdue must be False
    assert inv_data["is_overdue"] is False
    assert inv_data["days_late"] == 0

    # In dashboard, overdue_amount should be 0.00
    dash = client.get("/api/dashboard/summary", headers=headers).get_json()
    assert dash["cards"]["overdue_amount"] == "0.00"
    assert dash["cards"]["counts_by_status"]["overdue"] == 0


def test_edge_case_6_delete_client_with_invoices_blocked(client, create_user):
    """Edge Case 6: Deleting a client who has invoices -> blocked with explanation, never a FK error page."""
    user, headers = create_user(email="ec6@example.com")
    c_res = client.post("/api/clients", headers=headers, json={"name": "Client 6", "email": "c6@test.com"})
    cid = c_res.get_json()["id"]

    today = date.today().isoformat()
    client.post("/api/invoices", headers=headers, json={
        "invoice_number": "INV-CLIENT-FK",
        "client_id": cid,
        "issue_date": today,
        "due_date": today,
        "amount": "2500.00",
        "status": "draft",
    })

    # Delete client -> blocked with 409
    res_del = client.delete(f"/api/clients/{cid}", headers=headers)
    assert res_del.status_code == 409
    error_msg = res_del.get_json()["error"]
    assert "This client has 1 invoice" in error_msg
    assert "Delete or reassign them first" in error_msg
