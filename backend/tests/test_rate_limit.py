from app.rate_limit import RateLimiter


def test_allows_up_to_the_limit_then_blocks():
    limiter = RateLimiter(limit=3, window_seconds=60)
    assert limiter.allow("user-a")
    assert limiter.allow("user-a")
    assert limiter.allow("user-a")
    assert not limiter.allow("user-a")


def test_keys_are_independent():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("user-a")
    assert limiter.allow("user-b")
    assert not limiter.allow("user-a")
