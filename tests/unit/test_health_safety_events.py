"""Reproduction test for issue #68.

The `/health` endpoint is supposed to report how many safety events have
fired recently via the `safety_events_last_hour` field. Instead of reading
from `SafetyMonitor` (safety/monitoring.py), which already tracks
per-event-type counts in Redis, `health_check` hardcodes the field to 0
(api/routes/health.py:78). This test simulates safety events having been
recorded in Redis and asserts the health check reflects them -- it fails
today because the field is always 0 regardless of real activity.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.routes.health import health_check


@pytest.mark.unit
class TestHealthSafetyEventsReproduction:
    """Reproduces issue #68: safety_events_last_hour is a hardcoded placeholder."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.execute = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def mock_redis_instance(self) -> MagicMock:
        """A Redis client that reports safety events HAVE been recorded."""
        redis_instance = MagicMock()
        redis_instance.ping = MagicMock(return_value=True)
        # SafetyMonitor stores counts under "safety:events:<event_type>";
        # simulate one pii_detected event having fired in the last hour.
        redis_instance.get = MagicMock(
            side_effect=lambda key: "1" if key == "safety:events:pii_detected" else None
        )
        return redis_instance

    @pytest.mark.asyncio
    async def test_safety_events_last_hour_should_reflect_real_redis_counts(
        self, mock_db: AsyncMock, mock_redis_instance: MagicMock
    ) -> None:
        # NOTE: `core.config.Settings` only defines `redis_url`, not
        # `redis_host`/`redis_port` (which health.py reads). That's a
        # separate, pre-existing bug that makes the Redis dependency check
        # always report "unhealthy" -- unrelated to issue #68, so it's
        # patched around here to isolate the safety-events behavior.
        mock_settings = MagicMock(redis_host="localhost", redis_port=6379)
        with (
            patch("redis.Redis", return_value=mock_redis_instance),
            patch("core.config.settings", mock_settings),
        ):
            result = await health_check(db=mock_db)

        # EXPECTED: the endpoint should sum SafetyMonitor.get_event_count()
        # across VALID_EVENT_TYPES, so 1 recorded pii_detected event should
        # show up here.
        # ACTUAL (current bug): this is hardcoded to 0 in health.py, so the
        # assertion below fails, reproducing issue #68.
        assert result["safety_events_last_hour"] == 1
