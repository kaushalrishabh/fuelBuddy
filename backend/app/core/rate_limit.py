import time
from collections import defaultdict

WINDOW_SECONDS = 15 * 60
MAX_ATTEMPTS = 5

# In-memory is fine here: single user, single backend instance. Resets on
# restart, which only ever makes the limit more lenient, never less safe.
_attempts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str) -> bool:
    now = time.monotonic()
    recent = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]
    _attempts[key] = recent
    return len(recent) < MAX_ATTEMPTS


def record_attempt(key: str) -> None:
    _attempts[key].append(time.monotonic())


def reset_rate_limits() -> None:
    """For tests only, so failed-login tests don't bleed into each other."""
    _attempts.clear()
