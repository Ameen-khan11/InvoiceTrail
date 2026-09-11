import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import User


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    JWT_SECRET_KEY = "test-jwt-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FREE_PLAN_CLIENT_LIMIT = 5
    FREE_PLAN_INVOICE_LIMIT = 20
    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_SUPPRESS_SEND = True
    CORS_ORIGINS = ["http://localhost:5173"]


@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_user(app):
    """Factory fixture to create users and generate JWT auth headers."""
    def _create(email="user@example.com", name="Test User", password="Password123!", is_pro=False, business_name=None):
        user = User(name=name, email=email, is_pro=is_pro, business_name=business_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        headers = {"Authorization": f"Bearer {token}"}
        return user, headers

    return _create
