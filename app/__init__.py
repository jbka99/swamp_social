from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager

# @app.context_processor
# def inject_user():
#     return dict(user=current_user)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app