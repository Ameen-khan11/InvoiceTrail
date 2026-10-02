from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models import Client, Invoice, Payment


def test_dashboard_empty_state(client, create_user):
    user, headers = create_user(email="empty_dash@example.com")

    res = client.get("/api/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.get_json()

    # Empty state must return clean zeros, never null or NaN
    assert data["cards"]["total_outstanding"] == "0.00"
    assert data["cards"]["overdue_amount"] == "0.00"
    assert data["cards"]["paid_this_month"] == "0.00"
    assert data["cards"]["counts_by_status"]["draft"] == 0
    assert data["cards"]["counts_by_status"]["sent"] == 0
    assert data["cards"]["counts_by_status"]["overdue"] == 0
    assert data["overdue_invoices"] == []


def test_dashboard_summary_metrics(client, create_user):
    user, headers = create_user(email="dash_metrics@example.com")

    c = Client(user_id=user.id, name="Dash Client", email="dc@test.com")
    db.session.add(c)
    db.session.commit()

    today = date.today()

    # 1. Overdue sent invoice: 10,000 (due 10 days ago)
    inv1 = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="DASH-01",
        issue_date=today - timedelta(days=30),
        due_date=today - timedelta(days=10),
        amount=Decimal("10000.00"),
        status="sent",
    )
    # 2. Overdue partially paid invoice: 20,000 with 5,000 paid (balance 15,000, due 5 days ago)
    inv2 = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="DASH-02",
        issue_date=today - timedelta(days=20),
        due_date=today - timedelta(days=5),
        amount=Decimal("20000.00"),
        status="partially_paid",
    )
    # 3. Sent invoice not overdue: 8,000 (due in 10 days)
    inv3 = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="DASH-03",
        issue_date=today - timedelta(days=2),
        due_date=today + timedelta(days=10),
        amount=Decimal("8000.00"),
        status="sent",
    )
    # 4. Paid invoice: 5,000
    inv4 = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="DASH-04",
        issue_date=today - timedelta(days=15),
        due_date=today - timedelta(days=2),
        amount=Decimal("5000.00"),
        status="paid",
    )
    db.session.add_all([inv1, inv2, inv3, inv4])
    db.session.flush()

    # Payments (both within current calendar month so paid_this_month equals 10,000)
    p1 = Payment(
        user_id=user.id,
        invoice_id=inv2.id,
        amount=Decimal("5000.00"),
        paid_on=today.replace(day=1),
        method="bank",
    )
    p2 = Payment(
        user_id=user.id,
        invoice_id=inv4.id,
        amount=Decimal("5000.00"),
        paid_on=today - timedelta(days=1),
        method="upi",
    )
    db.session.add_all([p1, p2])
    db.session.commit()

    res = client.get("/api/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.get_json()

    # Total outstanding: inv1 (10,000) + inv2 balance (15,000) + inv3 (8,000) = 33,000
    assert data["cards"]["total_outstanding"] == "33000.00"

    # Overdue amount: inv1 (10,000) + inv2 balance (15,000) = 25,000
    assert data["cards"]["overdue_amount"] == "25000.00"

    # Paid this month: p1 (5,000) + p2 (5,000) = 10,000
    assert data["cards"]["paid_this_month"] == "10000.00"

    # Overdue invoices list: inv1 (10 days late) should appear before inv2 (5 days late)
    assert len(data["overdue_invoices"]) == 2
    assert data["overdue_invoices"][0]["invoice_number"] == "DASH-01"
    assert data["overdue_invoices"][0]["days_late"] == 10
    assert data["overdue_invoices"][1]["invoice_number"] == "DASH-02"
    assert data["overdue_invoices"][1]["days_late"] == 5


def test_dashboard_monthly_income(client, create_user):
    user, headers = create_user(email="income@example.com")

    res = client.get("/api/dashboard/monthly-income", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert "monthly_income" in data
    # Exactly 6 months
    assert len(data["monthly_income"]) == 6
    # Each entry has month and income
    for item in data["monthly_income"]:
        assert "month" in item
        assert "income" in item
