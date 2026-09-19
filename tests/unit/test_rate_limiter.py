from unittest.mock import MagicMock

import pytest
from fastapi import Request

from app.core.exceptions import RateLimitExceededException
from app.core.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_threshold() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60, key_prefix="test_allow")

    req = MagicMock(spec=Request)
    req.headers = {}
    req.client = MagicMock()
    req.client.host = "192.168.1.100"

    # Should allow 3 requests
    for _ in range(3):
        await limiter(req)

    # 4th request must raise RateLimitExceededException
    with pytest.raises(RateLimitExceededException) as exc_info:
        await limiter(req)

    assert exc_info.value.details.get("retry_after_seconds") == 60


@pytest.mark.asyncio
async def test_rate_limiter_differentiates_ips() -> None:

    limiter = RateLimiter(max_requests=2, window_seconds=60, key_prefix="test_ips")

    req1 = MagicMock(spec=Request)
    req1.headers = {}
    req1.client = MagicMock()
    req1.client.host = "10.0.0.1"

    req2 = MagicMock(spec=Request)
    req2.headers = {}
    req2.client = MagicMock()
    req2.client.host = "10.0.0.2"

    # Exhaust IP 1
    await limiter(req1)
    await limiter(req1)

    with pytest.raises(RateLimitExceededException):
        await limiter(req1)

    # IP 2 should still be allowed
    await limiter(req2)
    await limiter(req2)

    with pytest.raises(RateLimitExceededException):
        await limiter(req2)
