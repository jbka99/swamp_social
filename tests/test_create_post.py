def login(client):
    return client.post(
        "/login",
        data={"username": "testuser", "password": "password123"},
        follow_redirects=False
    )

def test_create_post_from_index(app, client, user_id):
    login(client)

    resp = client.post(
        "/",
        data={"title": "T", "body": "Hello"},
        follow_redirects=False
    )
    assert resp.status_code in (302, 200)

    from app.extensions import db
    from app.models import Post

    with app.app_context():
        post = db.session.query(Post).filter_by(user_id=user_id, title="T").first()
        assert post is not None
        assert post.content == "Hello"
