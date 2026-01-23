def test_homepage(client):
    resp = client.get("/")
    assert resp.status_code in (200, 302)