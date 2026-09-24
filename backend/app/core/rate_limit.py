"""
Generic Redis sliding-window rate limiter — Architecture.md §6.6.
Cross-cutting primitive (lives in core/, not a module-to-module call)
since both Analysis Orchestration (analyses/hour, concurrent in-flight)
and, in Phase 6, LLM Adapter (tokens/day) need it.
"""
from __future__ import annotations

import time
from typing import cast

import redis


class RateLimitExceeded(Exception):
    def __init__(self, key: str, limit: int, window_seconds: int):
        self.key = key
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(f"Rate limit exceeded for {key!r}: {limit}/{window_seconds}s")


def check_and_increment(
    redis_conn: redis.Redis, *, key: str, limit: int, window_seconds: int
) -> None:
    """Sorted-set sliding window: each call records `now` under `key`,
    prunes entries older than `window_seconds`, and raises if the
    remaining count meets or exceeds `limit`. Raises BEFORE recording
    the current attempt when already at the limit, so a rejected
    request doesn't itself count toward the window."""
    now = time.time()
    window_start = now - window_seconds

    redis_conn.zremrangebyscore(key, 0, window_start)
    # sync client at runtime; stub is generic over sync/async
    current_count = cast(int, redis_conn.zcard(key))
    if current_count >= limit:
        raise RateLimitExceeded(key, limit, window_seconds)

    redis_conn.zadd(key, {str(now): now})
    redis_conn.expire(key, window_seconds)


def check_and_increment_weighted(
    redis_conn: redis.Redis, *, key: str, weight: int, limit: int, window_seconds: int
) -> None:
    """Same sliding-window mechanism as check_and_increment, but each
    entry carries a weight (this module's own docstring names "LLM
    Adapter (tokens/day)" as the anticipated caller) summed within the
    window, rather than counting discrete events. Raises BEFORE
    recording the current attempt if the existing weighted sum alone
    already meets/exceeds the limit."""
    now = time.time()
    window_start = now - window_seconds

    redis_conn.zremrangebyscore(key, 0, window_start)
    entries = cast(list[bytes], redis_conn.zrange(key, 0, -1))
    current_weight = sum(int(entry.decode().rsplit(":", 1)[1]) for entry in entries)
    if current_weight >= limit:
        raise RateLimitExceeded(key, limit, window_seconds)

    # member must be unique per entry for a sorted set -- now alone
    # could collide across near-simultaneous calls, so weight and a
    # counter-like suffix ride along in the member string itself
    # (score stays the plain timestamp for windowing).
    redis_conn.zadd(key, {f"{now}:{weight}": now})
    redis_conn.expire(key, window_seconds)


def current_weighted_total(redis_conn: redis.Redis, *, key: str, window_seconds: int) -> int:
    now = time.time()
    redis_conn.zremrangebyscore(key, 0, now - window_seconds)
    entries = cast(list[bytes], redis_conn.zrange(key, 0, -1))
    return sum(int(entry.decode().rsplit(":", 1)[1]) for entry in entries)


def current_count(redis_conn: redis.Redis, *, key: str, window_seconds: int) -> int:
    now = time.time()
    redis_conn.zremrangebyscore(key, 0, now - window_seconds)
    return cast(int, redis_conn.zcard(key))
