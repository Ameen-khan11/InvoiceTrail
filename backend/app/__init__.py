from flask import Flask, jsonify
from app.config import config_by_name
from app.extensions import db, migrate, jwt, mail, cors


def create_app(env: str = "development") -> Flask:
    app = Flask(__name__)
    if isinstance(env, str):
        env_key = env.lower()
        app.config.from_object(config_by_name.get(env_key, config_by_name["development"]))
    elif env is not None:
        app.config.from_object(env)

    # --- bind extensions to this app ---
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

    # Import models so they register with SQLAlchemy metadata (needed for
    # migrations to detect tables) before any blueprints/queries run.
    with app.app_context():
        from app import models  # noqa: F401
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database table initialization notice: {e}")

    # --- blueprints ---
    from app.routes.auth import auth_bp
    from app.routes.clients import clients_bp
    from app.routes.invoices import invoices_bp
    from app.routes.payments import payments_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.settings import settings_bp
    from app.routes.public import public_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(clients_bp, url_prefix="/api/clients")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(payments_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(settings_bp, url_prefix="/api/settings")
    app.register_blueprint(public_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # --- consistent JSON error shape for uncaught HTTP errors ---
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error"}), 500

    return app
