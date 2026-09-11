from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.extensions import db
from app.models import Client, Invoice, User, ReminderLog
from cron_job import run_daily_reminders


def test_client_reminder_24h_cooldown(client, create_user):
    user, headers = create_user(email="remind_client@example.com")
    c = Client(user_id=user.id, name="Test Client", email="client@test.com")
    db.session.add(c)
    db.session.commit()

    today = date.today()
    inv = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="INV-REMIND-01",
        issue_date=today - timedelta(days=10),
        due_date=today - timedelta(days=2),
        amount=Decimal("5000.00"),
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # First send -> success 200
    res1 = client.post(f"/api/invoices/{inv.id}/remind", headers=headers)
    assert res1.status_code == 200
    assert "Reminder sent" in res1.get_json()["message"]
    assert res1.get_json()["invoice"]["last_reminder_sent_at"] is not None

    # Immediate second send -> 429 Cooldown
    res2 = client.post(f"/api/invoices/{inv.id}/remind", headers=headers)
    assert res2.status_code == 429
    assert "already sent in the last 24 hours" in res2.get_json()["error"]


def test_client_reminder_blocked_for_paid_invoice(client, create_user):
    user, headers = create_user(email="remind_paid@example.com")
    c = Client(user_id=user.id, name="Paid Client", email="paid_client@test.com")
    db.session.add(c)
    db.session.commit()

    today = date.today()
    inv = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="INV-PAID-REMIND",
        issue_date=today - timedelta(days=10),
        due_date=today - timedelta(days=2),
        amount=Decimal("5000.00"),
        status="paid",
    )
    db.session.add(inv)
    db.session.commit()

    res = client.post(f"/api/invoices/{inv.id}/remind", headers=headers)
    assert res.status_code == 422
    assert "Cannot send a reminder for a paid invoice" in res.get_json()["error"]


def test_cron_job_idempotency(app, create_user):
    # User 1: Has overdue invoice, email_reminders_enabled=True
    user1, _ = create_user(email="cron1@example.com", name="Cron User 1")
    user1.email_reminders_enabled = True

    # User 2: Reminders disabled
    user2, _ = create_user(email="cron2@example.com", name="Cron User 2")
    user2.email_reminders_enabled = False

    # User 3: Reminders enabled, but NO overdue invoices
    user3, _ = create_user(email="cron3@example.com", name="Cron User 3")
    user3.email_reminders_enabled = True

    c = Client(user_id=user1.id, name="Overdue Client", email="client_overdue@test.com")
    db.session.add(c)
    db.session.commit()

    today = date.today()
    inv = Invoice(
        user_id=user1.id,
        client_id=c.id,
        invoice_number="INV-CRON-OVERDUE",
        issue_date=today - timedelta(days=30),
        due_date=today - timedelta(days=5),
        amount=Decimal("12000.00"),
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # First run of daily job
    stats1 = run_daily_reminders(app=app)
    assert stats1["emails_sent"] == 1
    assert stats1["skipped_no_overdue"] == 1  # user3

    # Verify ReminderLog record created
    log = ReminderLog.query.filter_by(user_id=user1.id, sent_on=today).first()
    assert log is not None
    assert log.status == "sent"
    assert log.invoice_count == 1

    # Second run of daily job in the same day -> MUST NOT send any duplicate email!
    stats2 = run_daily_reminders(app=app)
    assert stats2["emails_sent"] == 0
    assert stats2["skipped_already_sent"] == 1  # user1 skipped because already sent today
