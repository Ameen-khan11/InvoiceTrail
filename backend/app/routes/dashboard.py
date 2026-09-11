from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import Invoice, Payment
from app.utils import current_user_id

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/summary")
@jwt_required()
def get_summary():
    uid = current_user_id()
    today = date.today()
    first_of_month = today.replace(day=1)

    # Subquery for total payments per invoice
    payment_subquery = (
        db.session.query(
            Payment.invoice_id,
            func.coalesce(func.sum(Payment.amount), 0).label("total_paid"),
        )
        .filter(Payment.user_id == uid)
        .group_by(Payment.invoice_id)
        .subquery()
    )

    # 1. Total Outstanding (invoices sent/partially_paid that have remaining balance)
    outstanding_result = (
        db.session.query(
            func.coalesce(
                func.sum(Invoice.amount - func.coalesce(payment_subquery.c.total_paid, 0)),
                0,
            )
        )
        .outerjoin(payment_subquery, Invoice.id == payment_subquery.c.invoice_id)
        .filter(
            Invoice.user_id == uid,
            Invoice.is_deleted == False,
            Invoice.status.in_(("sent", "partially_paid")),
        )
        .scalar()
    )
    total_outstanding = Decimal(str(outstanding_result or 0)).quantize(Decimal("0.01"))

    # 2. Overdue Amount (sent/partially_paid AND due_date < today)
    overdue_result = (
        db.session.query(
            func.coalesce(
                func.sum(Invoice.amount - func.coalesce(payment_subquery.c.total_paid, 0)),
                0,
            )
        )
        .outerjoin(payment_subquery, Invoice.id == payment_subquery.c.invoice_id)
        .filter(
            Invoice.user_id == uid,
            Invoice.is_deleted == False,
            Invoice.status.in_(("sent", "partially_paid")),
            Invoice.due_date < today,
        )
        .scalar()
    )
    overdue_amount = Decimal(str(overdue_result or 0)).quantize(Decimal("0.01"))

    # 3. Paid this month (sum of payments with paid_on in current calendar month)
    paid_this_month_result = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.user_id == uid,
            Payment.paid_on >= first_of_month,
            Payment.paid_on <= today,
        )
        .scalar()
    )
    paid_this_month = Decimal(str(paid_this_month_result or 0)).quantize(Decimal("0.01"))

    # 4. Invoice count by status
    status_counts_rows = (
        db.session.query(Invoice.status, func.count(Invoice.id))
        .filter(Invoice.user_id == uid, Invoice.is_deleted == False)
        .group_by(Invoice.status)
        .all()
    )
    status_counts = {
        "draft": 0,
        "sent": 0,
        "partially_paid": 0,
        "paid": 0,
        "cancelled": 0,
    }
    for st, count in status_counts_rows:
        status_counts[st] = count

    overdue_count = (
        db.session.query(func.count(Invoice.id))
        .filter(
            Invoice.user_id == uid,
            Invoice.is_deleted == False,
            Invoice.status.in_(("sent", "partially_paid")),
            Invoice.due_date < today,
        )
        .scalar()
        or 0
    )
    status_counts["overdue"] = overdue_count

    # 5. Overdue table: sorted by days overdue descending (due_date ASC)
    overdue_invoices_query = (
        Invoice.query.filter(
            Invoice.user_id == uid,
            Invoice.is_deleted == False,
            Invoice.status.in_(("sent", "partially_paid")),
            Invoice.due_date < today,
        )
        .order_by(Invoice.due_date.asc())
        .limit(10)
        .all()
    )

    overdue_list = []
    for inv in overdue_invoices_query:
        overdue_list.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "client_name": inv.client.name if inv.client else "Unknown",
            "amount": str(inv.amount),
            "balance_due": str(inv.balance_due),
            "currency": inv.currency,
            "due_date": inv.due_date.isoformat(),
            "days_late": inv.days_late,
        })

    return jsonify({
        "cards": {
            "total_outstanding": str(total_outstanding),
            "overdue_amount": str(overdue_amount),
            "paid_this_month": str(paid_this_month),
            "counts_by_status": status_counts,
        },
        "overdue_invoices": overdue_list,
    }), 200


@dashboard_bp.get("/monthly-income")
@jwt_required()
def get_monthly_income():
    uid = current_user_id()
    today = date.today()

    # Generate list of last 6 months: [{"year": y, "month": m, "label": "Jan 2026", "income": "0.00"}, ...]
    months = []
    for i in range(5, -1, -1):
        # Go back i months
        # Note: using simple month math
        month_idx = (today.month - 1 - i)
        year = today.year + (month_idx // 12)
        month = (month_idx % 12) + 1
        d = date(year, month, 1)
        months.append({
            "year": year,
            "month": month,
            "label": d.strftime("%b %Y"),
            "key": f"{year}-{month:02d}",
            "amount": Decimal("0.00"),
        })

    start_date = date(months[0]["year"], months[0]["month"], 1)

    # SQL aggregate payments grouped by year and month
    pyear_col = func.extract("year", Payment.paid_on)
    pmonth_col = func.extract("month", Payment.paid_on)

    rows = (
        db.session.query(
            pyear_col.label("pyear"),
            pmonth_col.label("pmonth"),
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
        )
        .filter(
            Payment.user_id == uid,
            Payment.paid_on >= start_date,
        )
        .group_by(pyear_col, pmonth_col)
        .all()
    )

    income_map = {}
    for r in rows:
        key = f"{int(r.pyear)}-{int(r.pmonth):02d}"
        income_map[key] = Decimal(str(r.total))

    result = []
    for m in months:
        val = income_map.get(m["key"], Decimal("0.00"))
        result.append({
            "month": m["label"],
            "income": str(val.quantize(Decimal("0.01"))),
        })

    return jsonify({"monthly_income": result}), 200
