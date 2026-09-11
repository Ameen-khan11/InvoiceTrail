from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Client, User
from app.utils import error_response, is_valid_email, require_fields, current_user_id, scoped_or_404

clients_bp = Blueprint("clients", __name__)


@clients_bp.get("")
@jwt_required()
def list_clients():
    uid = current_user_id()
    search = (request.args.get("search") or "").strip()

    query = Client.query.filter_by(user_id=uid)
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Client.name.ilike(like), Client.email.ilike(like), Client.company.ilike(like)))

    clients = query.order_by(Client.name.asc()).all()
    return jsonify({"clients": [c.to_dict() for c in clients]}), 200


@clients_bp.post("")
@jwt_required()
def create_client():
    uid = current_user_id()
    data = request.get_json(silent=True) or {}

    missing = require_fields(data, ["name", "email"])
    if missing:
        return error_response(f"{missing} is required", status=422, field=missing)

    if not is_valid_email(data["email"]):
        return error_response("Enter a valid email address", status=422, field="email")

    # --- free plan limit, enforced server-side ---
    user = db.session.get(User, uid)
    if not user.is_pro:
        current_count = Client.query.filter_by(user_id=uid).count()
        limit = current_app.config["FREE_PLAN_CLIENT_LIMIT"]
        if current_count >= limit:
            return error_response(
                f"Free plan is limited to {limit} clients. Upgrade to add more.", status=403
            )

    client = Client(
        user_id=uid,
        name=data["name"].strip(),
        email=data["email"].strip(),
        company=(data.get("company") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        notes=data.get("notes") or None,
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(client.to_dict()), 201


@clients_bp.get("/<int:client_id>")
@jwt_required()
def get_client(client_id):
    client = scoped_or_404(Client, client_id)
    if client is None:
        return error_response("Client not found", status=404)

    invoices = client.invoices.filter_by(is_deleted=False).all()
    total_billed = sum((inv.amount for inv in invoices), start=0)
    total_received = sum((inv.total_paid for inv in invoices), start=0)

    data = client.to_dict()
    data["invoices"] = [inv.to_dict() for inv in invoices]
    data["total_billed"] = str(total_billed)
    data["total_received"] = str(total_received)
    return jsonify(data), 200


@clients_bp.put("/<int:client_id>")
@jwt_required()
def update_client(client_id):
    client = scoped_or_404(Client, client_id)
    if client is None:
        return error_response("Client not found", status=404)

    data = request.get_json(silent=True) or {}

    if "email" in data and not is_valid_email(data["email"]):
        return error_response("Enter a valid email address", status=422, field="email")
    if "name" in data and not data["name"].strip():
        return error_response("Name cannot be blank", status=422, field="name")

    if "name" in data:
        client.name = data["name"].strip()
    if "email" in data:
        client.email = data["email"].strip()
    for field in ("company", "phone", "notes"):
        if field in data:
            value = data[field]
            setattr(client, field, value.strip() if isinstance(value, str) and value.strip() else None)

    db.session.commit()
    return jsonify(client.to_dict()), 200


@clients_bp.delete("/<int:client_id>")
@jwt_required()
def delete_client(client_id):
    client = scoped_or_404(Client, client_id)
    if client is None:
        return error_response("Client not found", status=404)

    # NOTE: this counts ALL invoices, including soft-deleted ones. A soft-deleted
    # invoice still holds a client_id foreign key, so deleting the client would
    # either orphan that row or violate the NOT NULL constraint on client_id.
    # Blocking here is what keeps that a clean 409 instead of a raw FK crash.
    invoice_count = client.invoices.count()
    if invoice_count > 0:
        return error_response(
            f"This client has {invoice_count} invoice{'s' if invoice_count != 1 else ''}. "
            "Delete or reassign them first.",
            status=409,
        )

    db.session.delete(client)
    db.session.commit()
    return "", 204
