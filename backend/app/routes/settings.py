from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import User, Client, Invoice
from app.utils import error_response, current_user_id

settings_bp = Blueprint("settings", __name__)


@settings_bp.get("")
@jwt_required()
def get_settings():
    uid = current_user_id()
    user = db.session.get(User, uid)
    if user is None:
        return error_response("User not found", status=404)

    client_count = Client.query.filter_by(user_id=uid).count()
    invoice_count = Invoice.query.filter_by(user_id=uid, is_deleted=False).count()

    client_limit = None if user.is_pro else current_app.config["FREE_PLAN_CLIENT_LIMIT"]
    invoice_limit = None if user.is_pro else current_app.config["FREE_PLAN_INVOICE_LIMIT"]

    return jsonify({
        "user": user.to_dict(),
        "usage": {
            "is_pro": user.is_pro,
            "clients": {
                "count": client_count,
                "limit": client_limit,
                "at_limit": (client_limit is not None and client_count >= client_limit),
            },
            "invoices": {
                "count": invoice_count,
                "limit": invoice_limit,
                "at_limit": (invoice_limit is not None and invoice_count >= invoice_limit),
            },
        },
    }), 200


@settings_bp.put("")
@jwt_required()
def update_settings():
    uid = current_user_id()
    user = db.session.get(User, uid)
    if user is None:
        return error_response("User not found", status=404)

    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = data["name"].strip()
        if not name:
            return error_response("Name cannot be blank", status=422, field="name")
        user.name = name

    if "business_name" in data:
        b_name = (data["business_name"] or "").strip()
        user.business_name = b_name or None

    if "email_reminders_enabled" in data:
        user.email_reminders_enabled = bool(data["email_reminders_enabled"])

    db.session.commit()

    return jsonify({
        "message": "Settings updated successfully",
        "user": user.to_dict(),
    }), 200
