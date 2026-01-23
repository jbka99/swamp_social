from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager
from flask_login import current_user

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from app.services import ensure_admin_flag

    @app.before_request
    def promote_admin_if_needed():
        if current_user.is_authenticated:
            ensure_admin_flag(current_user)

    # IMPORTANT:
    # Don't auto-create tables in production. Use Alembic migrations (`flask db upgrade`).
    # Auto-creating tables masks migration issues and does not apply schema changes.
    # If you want auto-create for local dev, set AUTO_CREATE_DB=1.
    if app.config.get("AUTO_CREATE_DB"):
        with app.app_context():
            from app.models import User, Post
            db.create_all()

    return app