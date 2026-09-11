from datetime import datetime, timezone
from app.extensions import db


class Client(db.Model):
    __tablename__ = "clients"
    __table_args__ = (
        db.Index("ix_clients_user_id", "user_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    invoices = db.relationship("Invoice", backref="client", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "company": self.company,
            "phone": self.phone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
