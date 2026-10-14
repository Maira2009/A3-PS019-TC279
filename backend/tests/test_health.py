def test_health_is_local_only(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0", "local_only": True}


def test_cors_restricts_unapproved_origin(client):
    response = client.options(
        "/health",
        headers={"Origin": "https://example.invalid", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers

