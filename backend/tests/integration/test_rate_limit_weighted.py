"""
Phase 9 / PRD §5 "token budgets for LLM calls": tests only the new
weighted-variant addition to core/rate_limit.py (check_and_increment
and current_count already existed from Phase 5 and are unchanged/
untested here — out of Phase 9's scope).
"""
import pytest

from app.core.rate_limit import (
    RateLimitExceeded,
    check_and_increment_weighted,
    current_weighted_total,
)
from app.core.redis_client import get_redis


@pytest.fixture
def redis_conn():
    conn = get_redis()
    yield conn
    for key in conn.keys("test_weighted:*"):
        conn.delete(key)


def test_weighted_sum_accumulates_across_calls(redis_conn):
    key = "test_weighted:accumulate"
    check_and_increment_weighted(redis_conn, key=key, weight=30, limit=100, window_seconds=60)
    check_and_increment_weighted(redis_conn, key=key, weight=40, limit=100, window_seconds=60)
    assert current_weighted_total(redis_conn, key=key, window_seconds=60) == 70


def test_weighted_check_raises_once_already_spent_amount_reaches_limit(redis_conn):
    # Matches check_and_increment's own established semantics exactly
    # (see its docstring): the gate checks the amount already
    # recorded against the limit, not "would this new amount push it
    # over" -- consistent with how the existing unweighted version
    # treats each call as needing to check the count-so-far first.
    key = "test_weighted:limit"
    check_and_increment_weighted(redis_conn, key=key, weight=100, limit=100, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        check_and_increment_weighted(redis_conn, key=key, weight=1, limit=100, window_seconds=60)


def test_weighted_check_does_not_record_the_rejected_attempt(redis_conn):
    key = "test_weighted:no-record-on-reject"
    check_and_increment_weighted(redis_conn, key=key, weight=100, limit=100, window_seconds=60)
    with pytest.raises(RateLimitExceeded):
        check_and_increment_weighted(redis_conn, key=key, weight=50, limit=100, window_seconds=60)
    # the rejected 50-weight attempt must not have been added
    assert current_weighted_total(redis_conn, key=key, window_seconds=60) == 100


def test_weighted_entries_outside_window_are_not_counted(redis_conn):
    key = "test_weighted:window"
    check_and_increment_weighted(redis_conn, key=key, weight=50, limit=1000, window_seconds=1)
    import time

    time.sleep(1.1)
    assert current_weighted_total(redis_conn, key=key, window_seconds=1) == 0


def test_current_weighted_total_zero_for_unused_key(redis_conn):
    total = current_weighted_total(
        redis_conn, key="test_weighted:never-used", window_seconds=60
    )
    assert total == 0
