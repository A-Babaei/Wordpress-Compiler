"""In-process sliding-window rate limiter.

Good enough for a single API instance. If you scale to multiple replicas,
implement the same `allow(key) -> bool` interface backed by Redis
(e.g. INCR + EXPIRE) and swap it in `main.py` — nothing else changes.
"""
import collections
import threading
import time


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = collections.defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.pop(0)
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
