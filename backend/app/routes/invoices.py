import csv
import io
from datetime import date, datetime, timezone

from flask import Blueprint, request, jsonify, current_app, Response, send_file
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Invoice, Client, User, Payment, INVOICE_STATUSES
from app.utils import error_response, require_fields, current_user_id, scoped_or_404
from app.services.pdf_generator import generate_invoice_pdf
from app.services.mailer import send_invoice_reminder

invoices_bp = Blueprint("invoices", __name__)

PER_PAGE = 20

# Statuses that come from the payments workflow, not a manual edit (see Phase 5).
SYSTEM_MANAGED_STATUSES = ("paid", "partially_paid")


def _parse_date(value, field_name):
    """Returns (date_obj, error_response_or_None)."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except (ValueError, TypeError):
        return None, error_response(f"{field_name} must be in YYYY-MM-DD format", status=422, field=field_name)


def _parse_amount(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount


@invoices_bp.get("")
@jwt_required()
def list_invoices():
    uid = current_user_id()

    status = request.args.get("status")
    client_id = request.args.get("client_id", type=int)
    search = (request.args.get("search") or "").strip()
    sort = request.args.get("sort", "due_date")
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    query = Invoice.query.filter_by(user_id=uid, is_deleted=False)

    if status:
        if status == "overdue":
            # derived state -> can't filter in SQL with a stored column, so
            # filter by the same rule as Invoice.is_overdue
            query = query.filter(
                Invoice.status.in_(("sent", "partially_paid")),
                Invoice.due_date < date.today(),
            )
        elif status in INVOICE_STATUSES:
            query = query.filter_by(status=status)
        else:
            return error_response(f"Unknown status '{status}'", status=422, field="status")

    if client_id:
        query = query.filter_by(client_id=client_id)

    if search:
        like = f"%{search}%"
        query = query.join(Client, Invoice.client_id == Client.id).filter(
            db.or_(Invoice.invoice_number.ilike(like), Client.name.ilike(like))
        )

    sort_map = {
        "due_date": Invoice.due_date.asc(),
        "-due_date": Invoice.due_date.desc(),
        "amount": Invoice.amount.asc(),
        "-amount": Invoice.amount.desc(),
    }
    if sort not in sort_map:
        return error_response(f"Unknown sort '{sort}'", status=422, field="sort")
    query = query.order_by(sort_map[sort])

    pagination = db.paginate(query, page=page, per_page=PER_PAGE, error_out=False)

    return jsonify({
        "invoices": [inv.to_dict(include_client=True) for inv in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": PER_PAGE,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
        },
    }), 200


@invoices_bp.post("")
@jwt_required()
def create_invoice():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}

    missing = require_fields(data, ["invoice_number", "client_id", "issue_date", "due_date", "amount"])
    if missing:
        return error_response(f"{missing} is required", status=422, field=missing)

    client = scoped_or_404(Client, data["client_id"], user_id=uid)
    if client is None:
        return error_response("Client not found", status=404, field="client_id")

    issue_date, err = _parse_date(data["issue_date"], "issue_date")
    if err:
        return err
    due_date, err = _parse_date(data["due_date"], "due_date")
    if err:
        return err
    if due_date < issue_date:
        return error_response("due_date must be on or after issue_date", status=422, field="due_date")

    amount = _parse_amount(data["amount"])
    if amount is None or amount <= 0:
        return error_response("amount must be a positive number", status=422, field="amount")

    status = data.get("status", "draft")
    if status not in INVOICE_STATUSES:
        return error_response(f"Unknown status '{status}'", status=422, field="status")
    if status in SYSTEM_MANAGED_STATUSES:
        return error_response(
            f"'{status}' is set automatically once payments are recorded, not on creation.",
            status=422, field="status",
        )

    # --- free plan limit ---
    user = db.session.get(User, uid)
    if not user.is_pro:
        current_count = Invoice.query.filter_by(user_id=uid, is_deleted=False).count()
        limit = current_app.config["FREE_PLAN_INVOICE_LIMIT"]
        if current_count >= limit:
            return error_response(
                f"Free plan is limited to {limit} invoices. Upgrade to add more.", status=403
            )

    invoice = Invoice(
        user_id=uid,
        client_id=client.id,
        invoice_number=data["invoice_number"].strip(),
        issue_date=issue_date,
        due_date=due_date,
        amount=amount,
        currency=(data.get("currency") or "PKR").strip().upper(),
        description=data.get("description") or None,
        status=status,
    )

    try:
        db.session.add(invoice)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("This invoice number already exists", status=409, field="invoice_number")

    return jsonify(invoice.to_dict(include_client=True)), 201


@invoices_bp.get("/<int:invoice_id>")
@jwt_required()
def get_invoice(invoice_id):
    invoice = scoped_or_404(Invoice, invoice_id)
    if invoice is None or invoice.is_deleted:
        return error_response("Invoice not found", status=404)

    data = invoice.to_dict(include_client=True)
    data["payments"] = [p.to_dict() for p in invoice.payments.order_by(Payment.paid_on).all()]
    return jsonify(data), 200


@invoices_bp.put("/<int:invoice_id>")
@jwt_required()
def update_invoice(invoice_id):
    uid = current_user_id()
    invoice = scoped_or_404(Invoice, invoice_id)
    if invoice is None or invoice.is_deleted:
        return error_response("Invoice not found", status=404)

    data = request.get_json(silent=True) or {}

    if "amount" in data:
        new_amount = _parse_amount(data["amount"])
        if new_amount is None or new_amount <= 0:
            return error_response("amount must be a positive number", status=422, field="amount")
        if invoice.status == "paid" and float(invoice.amount) != new_amount:
            return error_response(
                "Cannot edit the amount on a paid invoice. Cancel and reissue instead.",
                status=409, field="amount",
            )
        invoice.amount = new_amount

    if "client_id" in data:
        client = scoped_or_404(Client, data["client_id"], user_id=uid)
        if client is None:
            return error_response("Client not found", status=404, field="client_id")
        invoice.client_id = client.id

    if "issue_date" in data:
        issue_date, err = _parse_date(data["issue_date"], "issue_date")
        if err:
            return err
        invoice.issue_date = issue_date

    if "due_date" in data:
        due_date, err = _parse_date(data["due_date"], "due_date")
        if err:
            return err
        invoice.due_date = due_date

    if invoice.due_date < invoice.issue_date:
        return error_response("due_date must be on or after issue_date", status=422, field="due_date")

    if "invoice_number" in data:
        invoice.invoice_number = data["invoice_number"].strip()

    if "currency" in data:
        invoice.currency = data["currency"].strip().upper()

    if "description" in data:
        invoice.description = data["description"] or None

    if "status" in data:
        new_status = data["status"]
        if new_status not in INVOICE_STATUSES:
            return error_response(f"Unknown status '{new_status}'", status=422, field="status")
        if new_status in SYSTEM_MANAGED_STATUSES:
            return error_response(
                f"'{new_status}' is set automatically once payments are recorded, not by editing.",
                status=422, field="status",
            )
        invoice.status = new_status

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response("This invoice number already exists", status=409, field="invoice_number")

    return jsonify(invoice.to_dict(include_client=True)), 200


@invoices_bp.delete("/<int:invoice_id>")
@jwt_required()
def delete_invoice(invoice_id):
    invoice = scoped_or_404(Invoice, invoice_id)
    if invoice is None or invoice.is_deleted:
        return error_response("Invoice not found", status=404)

    invoice.is_deleted = True
    db.session.commit()
    return "", 204


@invoices_bp.post("/<int:invoice_id>/remind")
@jwt_required()
def remind_client(invoice_id):
    uid = current_user_id()
    invoice = scoped_or_404(Invoice, invoice_id, user_id=uid)
    if invoice is None or invoice.is_deleted:
        return error_response("Invoice not found", status=404)

    if invoice.status in ("paid", "cancelled"):
        return error_response(f"Cannot send a reminder for a {invoice.status} invoice", status=422)

    now = datetime.now(timezone.utc)
    if invoice.last_reminder_sent_at:
        # SQLite or MySQL can return naive or aware datetime
        last_sent = invoice.last_reminder_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if (now - last_sent).total_seconds() < 86400:
            return error_response("A reminder was already sent in the last 24 hours.", status=429)

    send_invoice_reminder(invoice)

    invoice.last_reminder_sent_at = now
    db.session.commit()

    return jsonify({
        "message": f"Reminder sent to {invoice.client.email}",
        "invoice": invoice.to_dict(include_client=True),
    }), 200


@invoices_bp.get("/export")
@jwt_required()
def export_invoices():
    uid = current_user_id()

    status = request.args.get("status")
    client_id = request.args.get("client_id", type=int)
    search = (request.args.get("search") or "").strip()
    sort = request.args.get("sort", "due_date")

    query = Invoice.query.filter_by(user_id=uid, is_deleted=False)

    if status:
        if status == "overdue":
            query = query.filter(
                Invoice.status.in_(("sent", "partially_paid")),
                Invoice.due_date < date.today(),
            )
        elif status in INVOICE_STATUSES:
            query = query.filter_by(status=status)

    if client_id:
        query = query.filter_by(client_id=client_id)

    if search:
        like = f"%{search}%"
        query = query.join(Client, Invoice.client_id == Client.id).filter(
            db.or_(Invoice.invoice_number.ilike(like), Client.name.ilike(like))
        )

    sort_map = {
        "due_date": Invoice.due_date.asc(),
        "-due_date": Invoice.due_date.desc(),
        "amount": Invoice.amount.asc(),
        "-amount": Invoice.amount.desc(),
    }
    if sort in sort_map:
        query = query.order_by(sort_map[sort])
    else:
        query = query.order_by(Invoice.due_date.asc())

    invoices = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice Number",
        "Client Name",
        "Client Email",
        "Issue Date",
        "Due Date",
        "Amount",
        "Currency",
        "Status",
        "Total Paid",
        "Balance Due",
    ])

    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.client.name if inv.client else "",
            inv.client.email if inv.client else "",
            inv.issue_date.isoformat() if inv.issue_date else "",
            inv.due_date.isoformat() if inv.due_date else "",
            str(inv.amount),
            inv.currency,
            inv.status,
            str(inv.total_paid),
            str(inv.balance_due),
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices.csv"},
    )


@invoices_bp.get("/<int:invoice_id>/pdf")
@jwt_required()
def download_invoice_pdf(invoice_id):
    invoice = scoped_or_404(Invoice, invoice_id)
    if invoice is None or invoice.is_deleted:
        return error_response("Invoice not found", status=404)

    pdf_buffer = generate_invoice_pdf(invoice)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Invoice-{invoice.invoice_number}.pdf",
    )
