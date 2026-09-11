import logging
from flask import current_app
from flask_mail import Message
from app.extensions import mail

logger = logging.getLogger(__name__)


def send_invoice_reminder(invoice, recipient_email=None, custom_note=None) -> bool:
    """Sends a polite payment reminder email for a specific invoice.
    
    Returns True if sent or simulated successfully, False if failed.
    """
    client = invoice.client
    user = invoice.user
    target_email = recipient_email or (client.email if client else None)
    if not target_email:
        logger.warning(f"Cannot send reminder for invoice #{invoice.invoice_number}: client has no email.")
        return False

    sender_name = user.business_name or user.name or "Your Freelancer"
    sender_email = current_app.config.get("MAIL_DEFAULT_SENDER") or "no-reply@invoicetrail.com"
    subject = f"Friendly Reminder: Invoice #{invoice.invoice_number} from {sender_name}"

    body_text = f"""Hello {client.name},

This is a friendly reminder that invoice #{invoice.invoice_number} for {invoice.currency} {invoice.balance_due:,.2f} was due on {invoice.due_date}.

Total Amount: {invoice.currency} {invoice.amount:,.2f}
Total Paid: {invoice.currency} {invoice.total_paid:,.2f}
Balance Due: {invoice.currency} {invoice.balance_due:,.2f}

{f'Note: {custom_note}' if custom_note else ''}

Please let us know once the payment has been initiated. Thank you for your business!

Best regards,
{sender_name}
"""

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #1e293b; margin-bottom: 8px;">Invoice Payment Reminder</h2>
        <p style="color: #64748b; margin-top: 0;">from <strong>{sender_name}</strong></p>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 16px 0;">
        <p>Dear {client.name},</p>
        <p>This is a gentle reminder regarding invoice <strong>#{invoice.invoice_number}</strong>.</p>
        
        <div style="background-color: #f8fafc; padding: 16px; border-radius: 6px; margin: 16px 0;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 6px 0; color: #64748b;">Due Date:</td><td style="font-weight: bold; text-align: right;">{invoice.due_date}</td></tr>
                <tr><td style="padding: 6px 0; color: #64748b;">Total Amount:</td><td style="font-weight: bold; text-align: right;">{invoice.currency} {invoice.amount:,.2f}</td></tr>
                <tr><td style="padding: 6px 0; color: #64748b;">Paid to Date:</td><td style="color: #16a34a; font-weight: bold; text-align: right;">{invoice.currency} {invoice.total_paid:,.2f}</td></tr>
                <tr style="border-top: 1px solid #cbd5e1;"><td style="padding: 10px 0 0; font-weight: bold; color: #0f172a;">Balance Remaining:</td><td style="padding: 10px 0 0; font-weight: bold; font-size: 18px; color: #dc2626; text-align: right;">{invoice.currency} {invoice.balance_due:,.2f}</td></tr>
            </table>
        </div>

        {f'<p style="background-color: #f1f5f9; padding: 10px; border-left: 3px solid #3b82f6; font-style: italic;">{custom_note}</p>' if custom_note else ''}

        <p style="color: #475569;">If payment has already been sent, please disregard this note. Otherwise, kindly settle at your earliest convenience.</p>
        <p style="color: #334155; margin-top: 24px;">Warm regards,<br><strong>{sender_name}</strong></p>
    </div>
    """

    # Check if mail server is actually configured or in testing/offline mode
    mail_server = current_app.config.get("MAIL_SERVER")
    if not mail_server or current_app.config.get("TESTING"):
        logger.info(f"[SIMULATED EMAIL] To: {target_email} | Subject: {subject}")
        return True

    try:
        msg = Message(
            subject=subject,
            sender=sender_email,
            recipients=[target_email],
            body=body_text,
            html=html_body,
        )
        mail.send(msg)
        logger.info(f"Successfully sent reminder email to {target_email} for invoice #{invoice.invoice_number}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send email to {target_email}: {exc}")
        return False


def send_overdue_digest(user, overdue_invoices) -> bool:
    """Sends a daily summary of overdue invoices to the freelancer/agency owner."""
    if not user.email:
        return False

    sender_email = current_app.config.get("MAIL_DEFAULT_SENDER") or "no-reply@invoicetrail.com"
    count = len(overdue_invoices)
    total_overdue = sum(inv.balance_due for inv in overdue_invoices)
    subject = f"InvoiceTrail Daily Digest: {count} overdue {'invoice' if count == 1 else 'invoices'}"

    lines = []
    for inv in overdue_invoices:
        client_name = inv.client.name if inv.client else "Unknown Client"
        lines.append(f"• #{inv.invoice_number} ({client_name}): {inv.currency} {inv.balance_due:,.2f} — {inv.days_late} days late")

    body_text = f"""Hello {user.name},

You have {count} invoice(s) currently overdue with total outstanding balance of {total_overdue:,.2f}:

{chr(10).join(lines)}

Log in to InvoiceTrail to review details or send 1-click reminders.
"""

    mail_server = current_app.config.get("MAIL_SERVER")
    if not mail_server or current_app.config.get("TESTING"):
        logger.info(f"[SIMULATED EMAIL DIGEST] To: {user.email} | Count: {count}")
        return True

    try:
        msg = Message(
            subject=subject,
            sender=sender_email,
            recipients=[user.email],
            body=body_text,
        )
        mail.send(msg)
        return True
    except Exception as exc:
        logger.error(f"Failed to send daily overdue digest to {user.email}: {exc}")
        return False
