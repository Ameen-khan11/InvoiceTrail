from datetime import datetime
from decimal import Decimal

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Invoice, Payment, PAYMENT_METHODS
from app.utils import error_response, require_fields, current_user_id, scoped_or_404

payments_bp = Blueprint("payments", __name__)


def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except (ValueError, TypeError):
        return None, error_response(f"{field_name} must be in YYYY-MM-DD format", status=422, field=field_name)


def _recalculate_invoice_status(invoice: Invoice) -> None:
    """Updates the invoice status according to total recorded payments."""
    total_paid = sum((Decimal(str(p.amount)) for p in invoice.payments), start=Decimal("0.00"))
    inv_amount = Decimal(str(invoice.amount))

    if total_paid >= inv_amount:
        invoice.status = "paid"
    elif total_paid > Decimal("0.00"):
        invoice.status = "partially_paid"
    else:
        # Revert to sent if it was previously paid/partially_paid
        if invoice.status in ("paid", "partially_paid"):
            invoice.status = "sent"


@payments_bp.post("/invoices/<int:invoice_id>/payments")
@jwt_required()
def record_payment(invoice_id):
    uid = current_user_id()
    invoice = scoped_or_404(Invoice, invoice_id, user_id=uid)
    if invoice is None or invoice.is_deleted:
        return error_response("Invoice not found", status=404)

    if invoice.status == "cancelled":
        return error_response("Cannot record payment against a cancelled invoice", status=422)

    data = request.get_json(silent=True) or {}
    missing = require_fields(data, ["amount", "paid_on"])
    if missing:
        return error_response(f"{missing} is required", status=422, field=missing)

    try:
        payment_amount = Decimal(str(data["amount"]))
    except (ValueError, TypeError, ArithmeticError):
        return error_response("amount must be a valid number", status=422, field="amount")

    if payment_amount <= Decimal("0.00"):
        return error_response("amount must be greater than 0", status=422, field="amount")

    paid_on, err = _parse_date(data["paid_on"], "paid_on")
    if err:
        return err

    method = (data.get("method") or "other").strip().lower()
    if method not in PAYMENT_METHODS:
        return error_response(f"method must be one of: {', '.join(PAYMENT_METHODS)}", status=422, field="method")

    # Check excess payment
    current_paid = sum((Decimal(str(p.amount)) for p in invoice.payments), start=Decimal("0.00"))
    inv_amount = Decimal(str(invoice.amount))
    balance_due = inv_amount - current_paid

    if payment_amount > balance_due:
        return error_response(
            f"Payment of {payment_amount} exceeds remaining balance of {balance_due}",
            status=422,
            field="amount",
        )

    payment = Payment(
        user_id=uid,
        invoice_id=invoice.id,
        amount=payment_amount,
        paid_on=paid_on,
        method=method,
        reference=(data.get("reference") or "").strip() or None,
    )
    db.session.add(payment)

    # Automatic status transition
    new_total_paid = current_paid + payment_amount
    if new_total_paid >= inv_amount:
        invoice.status = "paid"
    else:
        invoice.status = "partially_paid"

    db.session.commit()

    return jsonify({
        "payment": payment.to_dict(),
        "invoice": invoice.to_dict(include_client=True),
    }), 201


@payments_bp.delete("/payments/<int:payment_id>")
@jwt_required()
def delete_payment(payment_id):
    uid = current_user_id()
    payment = scoped_or_404(Payment, payment_id, user_id=uid)
    if payment is None:
        return error_response("Payment not found", status=404)

    invoice = payment.invoice

    db.session.delete(payment)
    db.session.flush()

    # Recalculate invoice status
    _recalculate_invoice_status(invoice)

    db.session.commit()
    return "", 204
