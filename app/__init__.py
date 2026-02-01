import os
from flask_socketio import SocketIO
from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager
from flask_login import current_user

socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_class=Config):
    from . import socket_events  # noqa
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    socketio.init_app(
        flask_app,
        async_mode=os.environ.get("SOCKETIO_ASYNC_MODE", "eventlet")
    )
    # дальше как у тебя
    is_dev = flask_app.config.get("IS_DEV", False)

    if not is_dev:
        if not flask_app.config.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY is not set")
        if not flask_app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError("DATABASE_URL is not set")
        flask_app.config["AUTO_CREATE_DB"] = False

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)

    # dev only: auto create tables when migrations are not in use
    if flask_app.config.get("AUTO_CREATE_DB", False):
        try:
            with flask_app.app_context():
                from . import models  # noqa: F401  (важно: регистрирует модели в metadata)

                from sqlalchemy import inspect
                engine = db.engine
                inspector = inspect(engine)
                tables = inspector.get_table_names()

                if not tables:
                    flask_app.logger.warning("AUTO_CREATE_DB=1: creating tables (empty db).")
                    db.create_all()

                    inspector = inspect(engine)
                    flask_app.logger.warning(f"AUTO_CREATE_DB: tables now: {inspector.get_table_names()}")
        except Exception:
            # даже если тут что-то падает — увидишь нормальный stacktrace
            flask_app.logger.exception("AUTO_CREATE_DB: error creating tables.")

    login_manager.init_app(flask_app)
    login_manager.login_view = 'routes.login'

    from app.routes import bp as main_bp
    flask_app.register_blueprint(main_bp)

    from app.services import ensure_admin_flag

    @flask_app.before_request
    def promote_admin_if_needed():
        if current_user.is_authenticated:
            ensure_admin_flag(current_user)

    return flask_app