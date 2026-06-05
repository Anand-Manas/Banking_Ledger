def test_health_check(client):
    """
    NOTE: app.py mounts health_router with prefix="/health"
    and health.py defines @router.get("/health").
    So the actual path is /health/health.
    """
    res = client.get("/health/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"