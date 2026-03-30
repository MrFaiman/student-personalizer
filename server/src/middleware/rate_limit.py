"""Rate limiting configuration (MoE section 4.3).

Set RATE_LIMIT_ENABLED=false to disable all rate limits (useful in test environments
where all requests share a single IP address and trigger limits immediately).
"""

import os
from collections.abc import Callable
from typing import Any

from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() not in ("0", "false", "no")

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def rate_limit(limit_string: str) -> Callable[[Any], Any]:
    """Apply a rate limit decorator, or a no-op when RATE_LIMIT_ENABLED=false."""
    if RATE_LIMIT_ENABLED:
        return limiter.limit(limit_string)
    return lambda f: f
