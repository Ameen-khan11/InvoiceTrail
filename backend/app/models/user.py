from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(120), unique=True, index=True, nullable=True)
    business_name = db.Column(db.String(150), nullable=True)

    is_pro = db.Column(db.Boolean, default=False, nullable=False)
    email_reminders_enabled = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    clients = db.relationship("Client", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    # --- password helpers ---
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    # --- serialization (never includes password_hash) ---
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "business_name": self.business_name,
            "is_pro": self.is_pro,
            "email_reminders_enabled": self.email_reminders_enabled,
            "google_connected": bool(self.google_id),
            "has_password": bool(self.password_hash),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
