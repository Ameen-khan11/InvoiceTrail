from flask import Blueprint, jsonify, send_file
from app.models import Invoice, Payment
from app.utils.errors import error_response
from app.services.pdf_generator import generate_invoice_pdf

public_bp = Blueprint("public", __name__, url_prefix="/api/public")


@public_bp.get("/invoices/<string:token>")
def get_public_invoice(token):
    """Public read-only invoice endpoint accessible to clients without logging in."""
    invoice = Invoice.query.filter_by(public_token=token, is_deleted=False).first()
    if invoice is None:
        return error_response("Invoice not found or invalid link", status=404)

    user = invoice.user
    client = invoice.client

    payments = [
        {
            "id": p.id,
            "amount": str(p.amount),
            "paid_on": p.paid_on.isoformat() if p.paid_on else None,
            "method": p.method,
            "reference": p.reference,
        }
        for p in invoice.payments.order_by(Payment.paid_on.desc()).all()
    ]

    return jsonify({
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "amount": str(invoice.amount),
            "currency": invoice.currency,
            "description": invoice.description,
            "status": invoice.status,
            "is_overdue": invoice.is_overdue,
            "days_late": invoice.days_late,
            "total_paid": str(invoice.total_paid),
            "balance_due": str(invoice.balance_due),
            "public_token": invoice.public_token,
        },
        "client": {
            "name": client.name if client else None,
            "email": client.email if client else None,
        },
        "business": {
            "name": user.business_name or user.name or "Freelancer",
            "email": user.email,
        },
        "payments": payments,
    }), 200


@public_bp.get("/invoices/<string:token>/pdf")
def download_public_invoice_pdf(token):
    """Download PDF for a public invoice token."""
    invoice = Invoice.query.filter_by(public_token=token, is_deleted=False).first()
    if invoice is None:
        return error_response("Invoice not found or invalid link", status=404)

    pdf_buffer = generate_invoice_pdf(invoice)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Invoice-{invoice.invoice_number}.pdf",
    )
