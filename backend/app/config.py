import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
# Load .env from backend directory if present
load_dotenv(os.path.join(os.path.dirname(basedir), ".env"))


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-please-32chars")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

    # --- Database ---
    # Supports TiDB Cloud (MySQL), PostgreSQL, and SQLite
    _db_url = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/invoicetrail"
    )
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    elif _db_url.startswith("mysql://"):
        # TiDB and cloud providers usually give mysql://user:pass@host:4000/db
        _db_url = _db_url.replace("mysql://", "mysql+pymysql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    _engine_options = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }
    # If connecting to TiDB Cloud Serverless, enforce secure SSL connection
    if "tidbcloud.com" in _db_url:
        import ssl
        _ca_path = os.environ.get("CA")
        if _ca_path and os.path.exists(_ca_path):
            _ssl_ctx = ssl.create_default_context(cafile=_ca_path)
        else:
            _ssl_ctx = ssl.create_default_context()
        _engine_options["connect_args"] = {"ssl": _ssl_ctx}

    SQLALCHEMY_ENGINE_OPTIONS = _engine_options

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me-please-32chars")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ["headers"]

    # --- Mail (Mailtrap in dev, real SMTP in prod) ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 2525))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@invoicetrail.app")

    # --- Business rules ---
    FREE_PLAN_CLIENT_LIMIT = 5
    FREE_PLAN_INVOICE_LIMIT = 20
    REMINDER_JOB_HOUR = 9  # server time, 24h clock

    # --- CORS ---
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MAIL_SUPPRESS_SEND = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
