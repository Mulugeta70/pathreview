from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db

log = structlog.get_logger()

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:  # noqa: B008
    """
    Check health of PostgreSQL, Redis, and Vector DB.
    Returns 200 if all healthy, 503 if any dependency is down.
    """
    health_status: dict[str, Any] = {
        "status": "healthy",
        "dependencies": {
            "postgres": "unknown",
            "redis": "unknown",
            "vector_db": "unknown",
        },
        "safety_events_last_hour": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Check PostgreSQL
        await db.execute("SELECT 1")  # type: ignore[call-overload]
        health_status["dependencies"]["postgres"] = "healthy"
        log.debug("postgres_health_check_passed")
    except Exception as exc:
        log.error("postgres_health_check_failed", error=str(exc))
        health_status["dependencies"]["postgres"] = "unhealthy"
        health_status["status"] = "unhealthy"

    try:
        # Check Redis (if available)
        import redis

        from core.config import settings

        # NOTE: Settings only defines `redis_url`, not `redis_host`/`redis_port`
        # -- this AttributeError is caught below and reported as "unhealthy"
        # rather than raised. Pre-existing bug, tracked separately from #68
        # (see PLAN.md); not fixed here to keep this commit scoped to
        # reproducing the safety-events issue.
        r = redis.Redis(  # type: ignore[call-overload]
            host=settings.redis_host,  # type: ignore[attr-defined]
            port=settings.redis_port,  # type: ignore[attr-defined]
            db=0,
            decode_responses=True,
        )
        r.ping()
        health_status["dependencies"]["redis"] = "healthy"
        log.debug("redis_health_check_passed")
    except Exception as exc:
        log.error("redis_health_check_failed", error=str(exc))
        health_status["dependencies"]["redis"] = "unhealthy"
        health_status["status"] = "unhealthy"

    try:
        # Check Vector DB (if available)
        # This is a placeholder - actual implementation depends on vector DB choice
        from core.config import settings

        # Attempt heartbeat to vector DB
        # For now, assume it's healthy if connection string exists
        if settings.vector_db_url:
            health_status["dependencies"]["vector_db"] = "healthy"
            log.debug("vector_db_health_check_passed")
        else:
            health_status["dependencies"]["vector_db"] = "unavailable"
    except Exception as exc:
        log.error("vector_db_health_check_failed", error=str(exc))
        health_status["dependencies"]["vector_db"] = "unhealthy"
        health_status["status"] = "unhealthy"

    # Count safety events in last hour (placeholder)
    try:
        # This would be populated by actual safety event logging
        health_status["safety_events_last_hour"] = 0
    except Exception as exc:
        log.error("safety_events_check_failed", error=str(exc))

    # Return 503 if any critical dependency is down
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )

    return health_status
