from datetime import datetime, timezone
from app.extensions import db


class ReminderLog(db.Model):
    __tablename__ = "reminder_log"
    __table_args__ = (
        # THIS constraint is the deduplication mechanism, not an `if` check in
        # Python. Two job runs racing each other can both pass a Python `if`,
        # but only one insert can win a unique index -> only one email sent.
        db.UniqueConstraint("user_id", "sent_on", name="uq_user_sent_on"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sent_on = db.Column(db.Date, nullable=False)
    invoice_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="sent")  # sent | failed

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sent_on": self.sent_on.isoformat() if self.sent_on else None,
            "invoice_count": self.invoice_count,
            "status": self.status,
        }
