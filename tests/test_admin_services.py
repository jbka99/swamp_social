from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User, Post


def test_ensure_admin_flag_promotes_user(app):
    from app.services import ensure_admin_flag

    with app.app_context():
        app.config["ADMIN_USERNAMES"] = {"admin"}

        admin = User(username="admin", password_hash=generate_password_hash("x"))
        db.session.add(admin)
        db.session.commit()

        assert admin.is_admin is False

        changed = ensure_admin_flag(admin)
        assert changed is True

        refreshed = db.session.get(User, admin.id)
        assert refreshed.is_admin is True


def test_admin_delete_user_removes_posts(app):
    from app.services import admin_delete_user

    with app.app_context():
        admin = User(username="root", is_admin=True, password_hash=generate_password_hash("x"))
        victim = User(username="victim", password_hash=generate_password_hash("x"))
        db.session.add_all([admin, victim])
        db.session.commit()

        db.session.add_all([
            Post(title="a", content="1", user_id=victim.id),
            Post(title="b", content="2", user_id=victim.id),
        ])
        db.session.commit()

        res = admin_delete_user(
            target_user_id=victim.id,
            actor_user_id=admin.id,
            actor_is_admin=True,
        )

        assert res.deleted is True
        assert res.reason == "ok"
        db.session.expire_all()
        assert db.session.get(User, victim.id) is None
        assert Post.query.filter_by(user_id=victim.id).count() == 0


def test_admin_bulk_delete_users_skips_actor(app):
    from app.services import admin_bulk_delete_users

    with app.app_context():
        admin = User(username="root", is_admin=True, password_hash=generate_password_hash("x"))
        u1 = User(username="u1", password_hash=generate_password_hash("x"))
        u2 = User(username="u2", password_hash=generate_password_hash("x"))
        db.session.add_all([admin, u1, u2])
        db.session.commit()

        res = admin_bulk_delete_users(
            target_user_ids=[admin.id, u1.id, u2.id],
            actor_user_id=admin.id,
            actor_is_admin=True,
        )

        assert res.deleted is True
        assert res.reason == "ok"
        db.session.expire_all()
        # actor жив
        assert db.session.get(User, admin.id) is not None
        # остальные удалены
        assert db.session.get(User, u1.id) is None
        assert db.session.get(User, u2.id) is None
