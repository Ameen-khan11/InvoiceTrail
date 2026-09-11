import json
import urllib.request
import urllib.error
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User
from app.utils import error_response, is_valid_email, require_fields

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}

    missing = require_fields(data, ["name", "email", "password"])
    if missing:
        return error_response(f"{missing} is required", status=422, field=missing)

    email = data["email"].strip().lower()
    password = data["password"]

    if not is_valid_email(email):
        return error_response("Enter a valid email address", status=422, field="email")

    if len(password) < 8:
        return error_response("Password must be at least 8 characters", status=422, field="password")

    if User.query.filter_by(email=email).first() is not None:
        return error_response("An account with this email already exists", status=409, field="email")

    user = User(name=data["name"].strip(), email=email, business_name=(data.get("business_name") or "").strip() or None)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        # Belt-and-braces: a race on the unique email index lands here as 409, never a 500.
        db.session.rollback()
        return error_response("An account with this email already exists", status=409, field="email")

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    missing = require_fields(data, ["email", "password"])
    if missing:
        return error_response(f"{missing} is required", status=422, field=missing)

    email = data["email"].strip().lower()
    user = User.query.filter_by(email=email).first()

    if user is None or not user.check_password(data["password"]):
        # Deliberately identical message for "no such user" and "wrong password" -
        # never reveal which one it was.
        return error_response("Invalid email or password", status=401)

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if user is None:
        return error_response("User not found", status=404)
    return jsonify(user.to_dict()), 200


@auth_bp.post("/google")
def google_auth():
    data = request.get_json(silent=True) or {}
    credential = data.get("credential")
    demo_email = data.get("demo_email")
    demo_name = data.get("demo_name")

    email = None
    name = None
    google_id = None

    if credential:
        # Verify with Google's public tokeninfo endpoint
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
            req = urllib.request.Request(url, headers={"User-Agent": "InvoiceTrail-Auth/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, Exception):
            return error_response("Invalid or expired Google credential", status=401)

        # Validate audience against configured Client ID if set
        google_client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        if google_client_id and payload.get("aud") != google_client_id:
            return error_response("Google token audience mismatch", status=401)

        # Check email verified
        email_verified = payload.get("email_verified")
        if str(email_verified).lower() not in ("true", "1"):
            return error_response("Google account email is not verified", status=400)

        email = (payload.get("email") or "").strip().lower()
        name = (payload.get("name") or "").strip()
        google_id = payload.get("sub")

    elif demo_email and (current_app.debug or current_app.testing or not current_app.config.get("GOOGLE_CLIENT_ID")):
        # Development / test mode fallback when Client ID is not configured
        email = demo_email.strip().lower()
        name = (demo_name or email.split("@")[0]).strip()
        google_id = f"demo_google_{email}"
    else:
        return error_response("Google credential is required", status=422, field="credential")

    if not email or not is_valid_email(email):
        return error_response("Invalid email returned from Google", status=400)

    if not name:
        name = email.split("@")[0].title()

    # Find existing user by google_id or email
    user = User.query.filter((User.google_id == google_id) | (User.email == email)).first()

    status_code = 200
    if user:
        # Link Google account if not linked
        if not user.google_id and google_id:
            user.google_id = google_id
        if not user.name and name:
            user.name = name
        db.session.commit()
    else:
        # Create new user via Google
        user = User(
            name=name,
            email=email,
            google_id=google_id,
            password_hash=None,
            business_name=f"{name}'s Studio"
        )
        try:
            db.session.add(user)
            db.session.commit()
            status_code = 201
        except IntegrityError:
            db.session.rollback()
            user = User.query.filter_by(email=email).first()
            if not user:
                return error_response("Failed to authenticate with Google", status=500)

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": user.to_dict()}), status_code

