"""RQ Queue wiring — analysis and explanation kept separate so a slow
or failed explanation job never blocks analysis throughput."""
from __future__ import annotations

from functools import lru_cache

import rq

from app.core.redis_client import get_redis


@lru_cache
def analysis_queue() -> rq.Queue:
    return rq.Queue("propagate-analyses", connection=get_redis())


@lru_cache
def explanation_queue() -> rq.Queue:
    return rq.Queue("propagate-explanations", connection=get_redis())
