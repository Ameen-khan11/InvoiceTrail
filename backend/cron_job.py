"""InvoiceTrail — Daily Overdue Invoices Reminder Job.

Runs once daily at 09:00 (or via manual execution / cron).
For each user with email_reminders_enabled=True and one or more overdue invoices:
1. Verifies no reminder was already sent to this user for today.
2. Inserts a ReminderLog row guarded by the UNIQUE(user_id, sent_on) database constraint.
   This guarantees that two jobs running simultaneously or sequentially in the same day
   can NEVER double-email the user.
3. Sends a polite digest email summarizing overdue invoices and the total overdue amount.
4. Catches SMTP errors per-user so a failure on one account does not halt the entire batch.
"""

import sys
from datetime import date, datetime
from decimal import Decimal

from flask_mail import Message
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db, mail
from app.models import User, Invoice, ReminderLog


def run_daily_reminders(app=None) -> dict:
    """Core logic of the reminder job.

    Returns a summary dict: {"users_checked": N, "emails_sent": N, "errors": N}.
    """
    if app is None:
        app = create_app()

    stats = {
        "users_checked": 0,
        "emails_sent": 0,
        "skipped_already_sent": 0,
        "skipped_no_overdue": 0,
        "errors": 0,
    }

    with app.app_context():
        today = date.today()
        app.logger.info(f"Starting daily reminder job for {today}")

        # Fetch eligible users: reminders enabled
        users = User.query.filter_by(email_reminders_enabled=True).all()
        stats["users_checked"] = len(users)

        for user in users:
            # 1. Python-level pre-check (fast path)
            existing_log = ReminderLog.query.filter_by(user_id=user.id, sent_on=today).first()
            if existing_log is not None:
                app.logger.info(f"User {user.id} ({user.email}) already reminded today ({today}). Skipping.")
                stats["skipped_already_sent"] += 1
                continue

            # 2. Find overdue invoices
            # Rule: due_date < today and status in ('sent', 'partially_paid') and not deleted
            overdue_invoices = (
                Invoice.query.filter(
                    Invoice.user_id == user.id,
                    Invoice.is_deleted == False,
                    Invoice.status.in_(("sent", "partially_paid")),
                    Invoice.due_date < today,
                )
                .order_by(Invoice.due_date.asc())
                .all()
            )

            if not overdue_invoices:
                # Silence is a feature — no email if no overdue invoices
                stats["skipped_no_overdue"] += 1
                continue

            # 3. Database-level deduplication: Insert ReminderLog BEFORE emailing
            # The UNIQUE(user_id, sent_on) constraint is the true atomic deduplicator.
            log_entry = ReminderLog(
                user_id=user.id,
                sent_on=today,
                invoice_count=len(overdue_invoices),
                status="pending",
            )
            try:
                db.session.add(log_entry)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                app.logger.warning(
                    f"Race condition caught: User {user.id} already received or is receiving today's reminder."
                )
                stats["skipped_already_sent"] += 1
                continue

            # 4. Calculate total overdue and compose email
            total_overdue = sum((inv.balance_due for inv in overdue_invoices), start=Decimal("0.00"))
            currency = overdue_invoices[0].currency if overdue_invoices else "PKR"

            invoice_lines = []
            for inv in overdue_invoices:
                client_name = inv.client.name if inv.client else "Client"
                invoice_lines.append(
                    f"  • #{inv.invoice_number} — {client_name}: {inv.currency} {inv.balance_due} "
                    f"(due {inv.due_date}, {inv.days_late} days overdue)"
                )
            invoices_text = "\n".join(invoice_lines)

            body_text = (
                f"Good morning {user.name},\n\n"
                f"You have {len(overdue_invoices)} overdue invoice{'s' if len(overdue_invoices) != 1 else ''} "
                f"totalling {currency} {total_overdue}:\n\n"
                f"{invoices_text}\n\n"
                f"Log in to InvoiceTrail to view details or send one-click reminders to your clients.\n\n"
                f"— InvoiceTrail Daily Summary\n"
                f"(You can disable these summaries in Settings)"
            )

            msg = Message(
                subject=f"InvoiceTrail: {len(overdue_invoices)} overdue invoice{'s' if len(overdue_invoices) != 1 else ''} ({currency} {total_overdue})",
                recipients=[user.email],
                body=body_text,
            )

            # 5. Send email with error isolation
            try:
                mail.send(msg)
                log_entry.status = "sent"
                db.session.commit()
                stats["emails_sent"] += 1
                app.logger.info(f"Reminder email dispatched to {user.email} for {len(overdue_invoices)} invoices.")
            except Exception as exc:
                app.logger.error(f"Failed to send email to {user.email}: {exc}")
                log_entry.status = "failed"
                db.session.commit()
                stats["errors"] += 1

        app.logger.info(f"Daily reminder job complete. Stats: {stats}")
        return stats


if __name__ == "__main__":
    result = run_daily_reminders()
    print("Reminder job finished:", result)
    sys.exit(0 if result["errors"] == 0 else 1)
