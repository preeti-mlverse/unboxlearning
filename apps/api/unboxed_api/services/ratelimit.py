"""A small sliding-window limiter for login, sign-up and reset attempts.

It lives in process memory, which is right for one API process. With several processes behind a load balancer,
move it to Redis (same interface)."""
import threading
import time
from collections import defaultdict, deque

from ..config import get_settings
from ..errors import AppError

_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def check(*parts: str) -> None:
    s = get_settings()
    key = "|".join(p.lower() for p in parts if p)
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > s.auth_rate_window_seconds:
            q.popleft()
        if len(q) >= s.auth_rate_limit:
            raise AppError(429, "RATE_LIMITED", "Too many attempts. Please wait a few minutes and try again.")
        q.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()
