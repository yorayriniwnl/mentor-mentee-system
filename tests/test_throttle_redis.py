import os
import time
import pytest

from rate_limiter import RateLimiter


@pytest.mark.skipif("REDIS_URL" not in os.environ, reason="Redis URL not configured")
def test_redis_rate_limiter():
    url = os.environ.get("REDIS_URL")
    rl = RateLimiter(redis_url=url)
    key = f"test:redis:{int(time.time())}"
    allowed, _ = rl.allow_request(key, limit=2, window=1)
    assert allowed
    allowed, _ = rl.allow_request(key, limit=2, window=1)
    assert allowed
    allowed, retry = rl.allow_request(key, limit=2, window=1)
    assert not allowed
    assert retry >= 0
    # reset and ensure allowed
    rl.reset(key)
    allowed, _ = rl.allow_request(key, limit=2, window=1)
    assert allowed
