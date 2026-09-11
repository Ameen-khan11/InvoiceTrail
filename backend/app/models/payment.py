from datetime import datetime, timezone
from app.extensions import db

PAYMENT_METHODS = ("cash", "bank", "upi", "card", "other")


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        db.Index("ix_payments_invoice_id", "invoice_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid_on = db.Column(db.Date, nullable=False)
    method = db.Column(db.Enum(*PAYMENT_METHODS, name="payment_method"), nullable=False, default="other")
    reference = db.Column(db.String(150), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "amount": str(self.amount),
            "paid_on": self.paid_on.isoformat() if self.paid_on else None,
            "method": self.method,
            "reference": self.reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
