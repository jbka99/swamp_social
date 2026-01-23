import pytest

from app import create_app
from app.extensions import db
from config import Config
from app.models import User
from werkzeug.security import generate_password_hash


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


@pytest.fixture
def app():
    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def user_id(app):
    with app.app_context():
        u = User(
            username="testuser",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(u)
        db.session.commit()

        uid = u.id  # сохранить до выхода из контекста/сессии
        return uid