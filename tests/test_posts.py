def login(client):
    return client.post(
        "/login",
        data={"username": "testuser", "password": "password123"},
        follow_redirects=False
    )

def test_owner_can_delete_post(app, client, user_id):
    login(client)

    from app.extensions import db
    from app.models import Post

    with app.app_context():
        post = Post(
            title="Test title",
            content="hello",
            user_id=user_id
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    resp = client.post(f"/post/{post_id}/delete", follow_redirects=False)
    assert resp.status_code in (302, 200)

    with app.app_context():
        deleted = db.session.get(Post, post_id)
        assert deleted is None