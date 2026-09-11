from app.routes.auth import auth_bp
from app.routes.clients import clients_bp
from app.routes.invoices import invoices_bp
from app.routes.payments import payments_bp
from app.routes.dashboard import dashboard_bp
from app.routes.settings import settings_bp

__all__ = [
    "auth_bp",
    "clients_bp",
    "invoices_bp",
    "payments_bp",
    "dashboard_bp",
    "settings_bp",
]
