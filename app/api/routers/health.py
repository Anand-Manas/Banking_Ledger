from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine
from app.utils.cache import get_redis_client

router = APIRouter()

@router.get("/health")
def health_check():
    """
    Health check endpoint for Docker/orchestration.
    Returns 200 only if both PostgreSQL and Redis are reachable.
    """
    health = {"status": "healthy", "services": {}}

    # Check PostgreSQL
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health["services"]["postgres"] = "up"
    except Exception as e:
        health["services"]["postgres"] = f"down: {str(e)}"
        health["status"] = "unhealthy"

    # Check Redis
    try:
        client = get_redis_client()
        client.ping()
        health["services"]["redis"] = "up"
    except Exception as e:
        health["services"]["redis"] = f"down: {str(e)}"
        health["status"] = "unhealthy"

    from fastapi import status
    code = status.HTTP_200_OK if health["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return health, code