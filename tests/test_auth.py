def test_login_works(client, user_id):
    resp = client.post(
        "/login",
        data={"username": "testuser", "password": "password123"},
        follow_redirects=False
    )
    assert resp.status_code in (302, 200)
