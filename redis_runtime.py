import logging
import time
from dataclasses import dataclass
from typing import Optional

from redis import Redis
from os import getenv
from redis.exceptions import RedisError

logger = logging.getLogger("voxa.redis")

REDIS_HEALTH_TTL_SECONDS = 15
REDIS_PING_TIMEOUT_SECONDS = 1


@dataclass
class RedisHealthState:
    healthy: bool = True
    last_checked: float = 0.0
    last_error: Optional[str] = None
    degraded_since: Optional[float] = None


class RedisRuntime:
    def __init__(self, client: Redis):
        self.client = client
        self.state = RedisHealthState()

    def is_healthy(self, force: bool = False) -> bool:
        now = time.time()

        if not force and (now - self.state.last_checked) < REDIS_HEALTH_TTL_SECONDS:
            return self.state.healthy

        try:
            self.client.ping()

            previously_healthy = self.state.healthy

            self.state.healthy = True
            self.state.last_checked = now
            self.state.last_error = None
            self.state.degraded_since = None

            if not previously_healthy:
                logger.warning(
                    "redis_recovered",
                    extra={
                        "event": "redis_recovered",
                        "checked_at": now,
                    },
                )

            return True

        except RedisError as exc:
            previously_healthy = self.state.healthy

            self.state.healthy = False
            self.state.last_checked = now
            self.state.last_error = str(exc)

            if self.state.degraded_since is None:
                self.state.degraded_since = now

            if previously_healthy:
                logger.error(
                    "redis_degraded",
                    extra={
                        "event": "redis_degraded",
                        "checked_at": now,
                        "error": str(exc),
                    },
                )

            return False

    def get_health_snapshot(self) -> dict:
        return {
            "healthy": self.state.healthy,
            "last_checked": self.state.last_checked,
            "last_error": self.state.last_error,
            "degraded_since": self.state.degraded_since,
        }

REDIS_URL = getenv("REDIS_URL", "redis://redis:6379/0")

redis_client = Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

redis_runtime = RedisRuntime(redis_client)
