def login(client):
    return client.post(
        "/login",
        data={"username": "testuser", "password": "password123"},
        follow_redirects=False
    )

def test_feed_paginates(app, client, user_id):
    login(client)

    from app.extensions import db
    from app.models import Post

    with app.app_context():
        for i in range(30):
            db.session.add(Post(title=f"T{i}", content="x", user_id=user_id))
        db.session.commit()

    r1 = client.get("/feed?page=1")
    assert r1.status_code == 200

    r2 = client.get("/feed?page=2")
    assert r2.status_code == 200
