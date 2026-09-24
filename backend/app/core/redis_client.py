"""Redis client — first real consumer of settings.REDIS_URL, which
was provisioned in Phase 0 but unwired until now."""
from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.REDIS_URL)
