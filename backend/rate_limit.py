import os
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client_id: str) -> bool:
        limit = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
        window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        now = time.monotonic()
        timestamps = self._requests[client_id]
        while timestamps and timestamps[0] <= now - window:
            timestamps.popleft()
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        return True


rate_limiter = InMemoryRateLimiter()

