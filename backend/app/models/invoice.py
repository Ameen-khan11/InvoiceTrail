import secrets
from datetime import datetime, timezone, date
from decimal import Decimal
from app.extensions import db

INVOICE_STATUSES = ("draft", "sent", "partially_paid", "paid", "cancelled")


class Invoice(db.Model):
    __tablename__ = "invoices"
    __table_args__ = (
        db.UniqueConstraint("user_id", "invoice_number", name="uq_user_invoice_number"),
        db.Index("ix_invoices_user_status", "user_id", "status"),
        db.Index("ix_invoices_user_due_date", "user_id", "due_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)

    invoice_number = db.Column(db.String(50), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)

    # Money is ALWAYS DECIMAL, never FLOAT.
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="PKR")
    description = db.Column(db.Text, nullable=True)

    status = db.Column(db.Enum(*INVOICE_STATUSES, name="invoice_status"), nullable=False, default="draft")

    public_token = db.Column(db.String(64), unique=True, index=True, nullable=True, default=lambda: secrets.token_urlsafe(32))
    last_reminder_sent_at = db.Column(db.DateTime, nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    payments = db.relationship("Payment", backref="invoice", lazy="dynamic", cascade="all, delete-orphan")

    # --- derived state, never stored ---
    @property
    def is_overdue(self) -> bool:
        """An invoice is overdue if it's sent/partially_paid AND past its due date.
        Rule: due_date is a calendar date, invoice becomes overdue the day AFTER
        due_date (i.e. due_date == today is NOT yet overdue). This rule must stay
        consistent between the dashboard and the reminder job.
        """
        if self.status not in ("sent", "partially_paid"):
            return False
        return self.due_date < date.today()

    @property
    def days_late(self) -> int:
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    @property
    def total_paid(self):
        total = sum((p.amount for p in self.payments), start=0)
        return total

    @property
    def balance_due(self):
        return self.amount - self.total_paid

    def to_dict(self, include_client=False) -> dict:
        data = {
            "id": self.id,
            "client_id": self.client_id,
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "status": self.status,
            "is_overdue": self.is_overdue,
            "days_late": self.days_late,
            "total_paid": str(self.total_paid),
            "balance_due": str(self.balance_due),
            "last_reminder_sent_at": self.last_reminder_sent_at.isoformat() if self.last_reminder_sent_at else None,
            "public_token": self.public_token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_client and self.client:
            data["client"] = {"id": self.client.id, "name": self.client.name, "email": self.client.email}
        return data
