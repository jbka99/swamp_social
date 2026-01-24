import os
from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager
from flask_login import current_user

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Compute IS_DEV once
    is_dev = app.config.get("IS_DEV", False)

    # # Debug logging in dev mode only
    # if is_dev:
    #     import logging
    #     from config import basedir
    #     logger = logging.getLogger(__name__)
    #     logger.setLevel(logging.INFO)
    #     if not logger.handlers:
    #         handler = logging.StreamHandler()
    #         handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    #         logger.addHandler(handler)
    #     logger.info("=" * 60)
    #     logger.info("DEV MODE - Configuration Debug Info:")
    #     logger.info(f"  Current working directory: {os.getcwd()}")
    #     logger.info(f"  Project root (basedir): {basedir}")
    #     logger.info(f"  SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')}")
    #     
    #     # Sanity check: verify instance directory is writable (SQLite only)
    #     db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    #     if db_uri and db_uri.startswith('sqlite:///'):
    #         import tempfile
    #         # Extract path from URI
    #         db_path = db_uri[10:]  # Remove 'sqlite:///'
    #         instance_dir = os.path.dirname(db_path)
    #         if instance_dir:
    #             try:
    #                 # Try to create a temp file in instance directory
    #                 test_file = os.path.join(instance_dir, '.write_test')
    #                 with open(test_file, 'w') as f:
    #                     f.write('test')
    #                 os.remove(test_file)
    #                 logger.info(f"  Instance directory writable: {instance_dir}")
    #             except Exception as e:
    #                 logger.error(f"  ERROR: Instance directory not writable: {instance_dir}")
    #                 logger.error(f"  Error: {e}")
    #     
    #     logger.info("=" * 60)

    # Validate required config in production
    if not is_dev:
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY is not set")
        if not app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError("DATABASE_URL is not set")

    # Force disable AUTO_CREATE_DB if not dev
    if not is_dev:
        app.config["AUTO_CREATE_DB"] = False

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
            from app.models import User, Thread
            db.create_all()

    return app